import os
import sys
import logging
import subprocess
from notifiers.notification_manager import NotificationManager
from config_manager import ConfigManager

# --- 日志基础配置 ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

# --- 初始化配置管理器 ---
config_mgr = ConfigManager()

# --- 从配置和环境变量加载设置 (环境变量优先) ---

# 基础配置
DOMAIN = config_mgr.get('general.domain', 'DOMAIN')
DNS_API = config_mgr.get('general.dns_api', 'DNS_API')
ACME_EMAIL = config_mgr.get('general.acme_email', 'ACME_EMAIL')
CERT_OUTPUT_PATH = config_mgr.get('general.cert_output_path', 'CERT_OUTPUT_PATH', '/output')

# Synology 部署配置
AUTO_DEPLOY_TO_SYNOLOGY = str(config_mgr.get('synology.auto_deploy', 'AUTO_DEPLOY_TO_SYNOLOGY', 'false')).lower() == 'true'
SYNO_USERNAME = config_mgr.get('synology.username', 'SYNO_Username')
SYNO_PASSWORD = config_mgr.get('synology.password', 'SYNO_Password')
SYNO_PORT = config_mgr.get('synology.port', 'SYNO_Port')
SYNO_PROTOCOL = config_mgr.get('synology.protocol', 'SYNO_Protocol')


# 初始化通知管理器
notification_mgr = NotificationManager()


def validate_config():
    """检查核心的配置是否都已设置"""
    logging.info("开始验证配置...")
    
    required_vars = {
        'DOMAIN': DOMAIN,
        'DNS_API': DNS_API,
        'ACME_EMAIL': ACME_EMAIL,
    }

    # 注意：DNS 提供商的特定 API 凭证 (如 DP_Id, CF_Token) 由 acme.sh 自行验证。
    # 如果缺失，acme.sh 会提供非常明确的错误信息，这比我们在这里做通用检查要好。

    if AUTO_DEPLOY_TO_SYNOLOGY:
        logging.info("检测到已启用 Synology 自动部署，将验证 DSM 相关配置。")
        required_vars.update({
            'SYNO_Username': SYNO_USERNAME,
            'SYNO_Password': SYNO_PASSWORD,
            'SYNO_Port': SYNO_PORT,
            'SYNO_Protocol': SYNO_PROTOCOL
        })

    missing_vars = [k for k, v in required_vars.items() if not v]
    if missing_vars:
        error_msg = f"错误：缺少必要的配置项: {', '.join(missing_vars)}。请在环境变量或 config.json 中设置它们。"
        logging.error(error_msg)
        notification_mgr.dispatch("failure", DOMAIN, details=error_msg)
        sys.exit(1)
        
    logging.info("配置验证通过。")


def run_command(command, env_vars=None):
    """执行一个 shell 命令并返回成功状态和输出"""
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
        
    try:
        process = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=env
        )
        logging.info(f"命令 '{' '.join(command)}' 执行成功。")
        logging.debug(f"输出:\n{process.stdout}")
        return True, process.stdout
    except subprocess.CalledProcessError as e:
        # 将标准输出和标准错误都记录下来，因为acme.sh有时会将信息输出到stdout
        error_output = f"标准输出:\n{e.stdout}\n标准错误:\n{e.stderr}"
        full_error_log = f"命令 '{' '.join(command)}' 执行失败。\n返回码: {e.returncode}\n{error_output}"
        logging.error(full_error_log)
        # 返回合并后的错误信息，以便发送通知
        return False, f"{e.stdout}\n{e.stderr}".strip()


def setup_acme_account():
    """注册 acme.sh 账户并设置默认 CA"""
    logging.info("正在设置 acme.sh 账户...")
    acme_sh_path = '/root/.acme.sh/acme.sh'
    
    register_cmd = [acme_sh_path, '--register-account', '-m', ACME_EMAIL]
    success, _ = run_command(register_cmd)
    if not success:
        logging.warning("账户注册命令失败，可能已经注册。将继续执行。")

    set_ca_cmd = [acme_sh_path, '--set-default-ca', '--server', 'letsencrypt']
    success, _ = run_command(set_ca_cmd)
    if not success:
        logging.error("设置默认 CA 失败。")
        return False
        
    return True


def issue_or_renew_cert():
    """执行证书申请或续签的核心逻辑"""
    logging.info(f"开始为域名 *. {DOMAIN} 和 {DOMAIN} 申请/续签证书...")
    acme_sh_path = '/root/.acme.sh/acme.sh'
    
    issue_command = [
        acme_sh_path, '--issue', '--dns', DNS_API,
        '-d', DOMAIN, '-d', f'*.{DOMAIN}',
        '--keylength', 'ec-256', '--log'
    ]

    # 【关键改动】
    # 动态准备需要传递给 acme.sh 的环境变量。
    # 这会自动抓取所有相关的 DNS 提供商的环境变量，例如 DP_Id, DP_Key, CF_Token 等。
    dns_api_prefixes = ('DP_', 'CF_', 'ALI_', 'GD_', 'HE_', 'CLOUDXNS_', 'GODADDY_')
    command_env = {k: v for k, v in os.environ.items() if k.startswith(dns_api_prefixes)}

    if AUTO_DEPLOY_TO_SYNOLOGY:
        logging.info("添加 synology_dsm 部署钩子到命令中。")
        issue_command.extend(['--deploy-hook', 'synology_dsm'])
        # 将群晖凭证添加到命令的环境中，供部署钩子使用
        command_env.update({
            'SYNO_Username': SYNO_USERNAME,
            'SYNO_Password': SYNO_PASSWORD,
            'SYNO_Port': str(SYNO_PORT),
            'SYNO_Protocol': SYNO_PROTOCOL
        })

    success, output = run_command(issue_command, env_vars=command_env)
    
    if not success:
        error_message = f"证书申请/续签失败。错误详情: \n{output}"
        logging.error(error_message)
        return False, output
    
    success_message = "证书申请/续签命令执行成功。"
    if AUTO_DEPLOY_TO_SYNOLOGY:
        success_message += " 已触发部署到 Synology DSM 的流程。"
    
    logging.info(success_message)
    return True, ""


def install_cert():
    """将生成的证书文件拷贝到指定的输出目录"""
    logging.info(f"开始将证书安装到输出目录: {CERT_OUTPUT_PATH}")
    acme_sh_path = '/root/.acme.sh/acme.sh'
    
    try:
        os.makedirs(CERT_OUTPUT_PATH, exist_ok=True)
    except OSError as e:
        error_msg = f"创建输出目录 {CERT_OUTPUT_PATH} 失败: {e}"
        logging.error(error_msg)
        return False, error_msg

    install_command = [
        acme_sh_path, '--install-cert',
        '-d', DOMAIN,
        '--key-file', os.path.join(CERT_OUTPUT_PATH, 'privkey.pem'),
        '--fullchain-file', os.path.join(CERT_OUTPUT_PATH, 'fullchain.pem'),
        '--reloadcmd', 'echo "Certificate installed."'
    ]

    success, error_output = run_command(install_command)
    if not success:
        error_message = f"将证书文件安装到 {CERT_OUTPUT_PATH} 失败: {error_output}"
        logging.error(error_message)
        return False, error_message

    logging.info(f"证书已成功安装到 {CERT_OUTPUT_PATH}")
    return True, ""


if __name__ == "__main__":
    logging.info("--- Synology 证书续签工具启动 ---")
    
    validate_config()
    
    if not setup_acme_account():
        error_msg = "acme.sh 账户设置失败，程序终止。"
        logging.error(error_msg)
        notification_mgr.dispatch("failure", DOMAIN, details=error_msg)
        sys.exit(1)

    issue_success, issue_error = issue_or_renew_cert()

    if issue_success:
        install_success, install_error = install_cert()
        
        if install_success:
            success_details = f"证书已成功续签并保存到 {CERT_OUTPUT_PATH}。"
            if AUTO_DEPLOY_TO_SYNOLOGY:
                success_details += "\n已尝试自动部署到 Synology DSM。"
            logging.info("--- 证书自动化任务成功完成 ---")
            notification_mgr.dispatch("success", DOMAIN, details=success_details)
        else:
            warning_details = f"证书续签/部署到 DSM 可能已成功，但保存证书到 {CERT_OUTPUT_PATH} 失败: {install_error}"
            logging.warning(warning_details)
            notification_mgr.dispatch("success", DOMAIN, details=warning_details)
    else:
        logging.error("--- 证书自动化任务失败 ---")
        notification_mgr.dispatch("failure", DOMAIN, details=issue_error)
        sys.exit(1)

