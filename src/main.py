import os
import sys
import json
import logging
import subprocess
# 导入路径不变，因为 Python 会自动将执行脚本的目录加入 path
from notifiers.notification_manager import NotificationManager

# --- 配置日志记录 ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

# --- 加载外部配置文件 ---
try:
    # 更新配置文件的绝对路径
    with open('/app/src/config/config.json', 'r') as f:
        config = json.load()
except (FileNotFoundError, json.JSONDecodeError) as e:
    logging.warning(f"无法加载或解析 config.json 文件: {e}。将使用默认值。")
    config = {"certificate": {}}

# --- 从环境变量或配置文件读取配置 ---
# (此部分及后续函数内容保持不变, 这里省略以保持简洁)
# ...
DOMAIN = os.environ.get('DOMAIN')
DNS_API = os.environ.get('DNS_API')
API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')
ACME_EMAIL = os.environ.get('ACME_EMAIL')
RENEW_DAYS = os.environ.get('RENEW_DAYS', '30')

cert_config = config.get('certificate', {})
CERT_OUTPUT_PATH = os.environ.get('CERT_OUTPUT_PATH') or cert_config.get('output_path') or '/output'
KEY_FILENAME = os.environ.get('KEY_FILENAME') or cert_config.get('key_filename') or 'privkey.pem'
FULLCHAIN_FILENAME = os.environ.get('FULLCHAIN_FILENAME') or cert_config.get('fullchain_filename') or 'fullchain.pem'
CERT_FILENAME = os.environ.get('CERT_FILENAME') or cert_config.get('cert_filename') or 'cert.pem'
CA_FILENAME = os.environ.get('CA_FILENAME') or cert_config.get('ca_filename') or 'ca.pem'


def validate_config():
    """检查必要的环境变量是否都已设置"""
    global DOMAIN
    required_vars = ['DOMAIN', 'DNS_API', 'API_KEY', 'API_SECRET', 'ACME_EMAIL']
    missing_vars = [var for var in required_vars if not globals().get(var)]
    if missing_vars:
        logging.error(f"错误：缺少必要的环境变量: {', '.join(missing_vars)}")
        sys.exit(1)
    
    if DOMAIN.startswith('*.'):
        original_domain = DOMAIN
        DOMAIN = DOMAIN[2:]
        logging.warning(f"检测到域名输入为 '{original_domain}'，已自动修正为基础域名: '{DOMAIN}'")
        
    if DNS_API.lower() not in ['dns_dp', 'dns_ali']:
        logging.error(f"错误: 不支持的 DNS_API '{DNS_API}'.")
        sys.exit(1)
    
    logging.info("环境变量配置验证通过。")
    logging.info(f"证书将在到期前 {RENEW_DAYS} 天进行续签。")

def run_command(command, suppress_errors=False):
    """执行 shell 命令并记录输出, 返回 (bool, str)"""
    logging.info(f"执行命令: {' '.join(command)}")
    try:
        process = subprocess.run(
            command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8'
        )
        if process.stdout: logging.info(f"命令输出:\n{process.stdout}")
        if process.stderr: logging.warning(f"命令错误输出:\n{process.stderr}")
        return True, ""
    except subprocess.CalledProcessError as e:
        error_message = e.stderr or e.stdout
        if not suppress_errors:
            logging.error(f"命令执行失败! 返回码: {e.returncode}")
            if e.stdout: logging.error(f"失败输出:\n{e.stdout}")
            if e.stderr: logging.error(f"失败错误输出:\n{e.stderr}")
        return False, error_message
        
def set_api_credentials():
    logging.info(f"为 {DNS_API} 设置 API 凭证...")
    if DNS_API.lower() == 'dns_dp':
        os.environ['DP_Id'] = API_KEY
        os.environ['DP_Key'] = API_SECRET
    elif DNS_API.lower() == 'dns_ali':
        os.environ['Ali_Key'] = API_KEY
        os.environ['Ali_Secret'] = API_SECRET
    logging.info("API 凭证设置完成。")

def setup_acme_sh():
    acme_sh_path = '/root/.acme.sh/acme.sh'
    logging.info("设置 acme.sh 默认 CA 为 Let's Encrypt...")
    run_command([acme_sh_path, '--set-default-ca', '--server', 'letsencrypt'], suppress_errors=True)
    
    logging.info(f"设置证书自动续订周期为 {RENEW_DAYS} 天...")
    run_command([acme_sh_path, '--set-renew-days', RENEW_DAYS], suppress_errors=True)

def issue_or_renew_cert():
    logging.info(f"开始为域名 *. {DOMAIN} 和 {DOMAIN} 申请/续签证书...")
    acme_sh_path = '/root/.acme.sh/acme.sh'
    issue_command = [
        acme_sh_path, '--issue', '--dns', DNS_API,
        '-d', DOMAIN, '-d', f'*.{DOMAIN}',
        '--keylength', 'ec-256', '--log'
    ]
    success, error_output = run_command(issue_command)
    if not success:
        logging.error("证书申请/续签失败。")
        return False, error_output
    logging.info("证书申请/续签命令执行成功。")
    return True, ""

def install_cert():
    full_key_path = os.path.join(CERT_OUTPUT_PATH, KEY_FILENAME)
    full_chain_path = os.path.join(CERT_OUTPUT_PATH, FULLCHAIN_FILENAME)
    full_cert_path = os.path.join(CERT_OUTPUT_PATH, CERT_FILENAME)
    full_ca_path = os.path.join(CERT_OUTPUT_PATH, CA_FILENAME)
    
    logging.info(f"准备将证书安装到指定位置...")
    
    if not os.path.exists(CERT_OUTPUT_PATH):
        try:
            os.makedirs(CERT_OUTPUT_PATH)
            logging.info(f"目录 {CERT_OUTPUT_PATH} 创建成功。")
        except OSError as e:
            logging.error(f"创建目录 {CERT_OUTPUT_PATH} 失败: {e}")
            return False, str(e)

    acme_sh_path = '/root/.acme.sh/acme.sh'
    install_command = [
        acme_sh_path, '--install-cert', '-d', DOMAIN, '--ecc',
        '--key-file', full_key_path,
        '--fullchain-file', full_chain_path,
        '--cert-file', full_cert_path,
        '--ca-file', full_ca_path
    ]
    success, error_output = run_command(install_command)
    if not success:
        logging.error("证书安装失败。")
        return False, error_output
    logging.info(f"证书及密钥文件已成功安装到 {CERT_OUTPUT_PATH} 目录。")
    return True, ""

if __name__ == "__main__":
    notification_mgr = NotificationManager()
    
    try:
        logging.info("--- 开始执行证书自动化任务 ---")
        
        validate_config()
        set_api_credentials()
        setup_acme_sh()
        
        issue_success, issue_error = issue_or_renew_cert()
        if issue_success:
            install_success, install_error = install_cert()
            if install_success:
                logging.info("--- 证书自动化任务成功完成 ---")
                notification_mgr.dispatch("success", DOMAIN)
            else:
                error_details = f"证书安装失败: {install_error}"
                logging.error(f"--- 任务失败于证书安装阶段 ---: {error_details}")
                notification_mgr.dispatch("failure", DOMAIN, details=error_details)
                sys.exit(1)
        else:
            error_details = f"证书申请失败: {issue_error}"
            logging.error(f"--- 任务失败于证书申请/续签阶段 ---: {error_details}")
            notification_mgr.dispatch("failure", DOMAIN, details=error_details)
            sys.exit(1)
            
    except Exception as e:
        domain_for_notification = DOMAIN if 'DOMAIN' in globals() and DOMAIN else "未知"
        error_details = f"脚本发生严重错误: {e}"
        logging.critical(f"--- {error_details} ---", exc_info=True)
        notification_mgr.dispatch("failure", domain_for_notification, details=error_details)
        sys.exit(1)
