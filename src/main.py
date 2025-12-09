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
AUTO_DEPLOY_TO_SYNOLOGY = config_mgr.get('synology.auto_deploy', 'AUTO_DEPLOY_TO_SYNOLOGY', False)
SYNO_USERNAME = config_mgr.get('synology.username', 'SYNO_USERNAME')
SYNO_PASSWORD = config_mgr.get('synology.password', 'SYNO_PASSWORD')
SYNO_PORT = config_mgr.get('synology.port', 'SYNO_PORT')
SYNO_SCHEME = config_mgr.get('synology.scheme', 'SYNO_SCHEME')
SYNO_HOSTNAME = config_mgr.get('synology.hostname', 'SYNO_HOSTNAME')
SYNO_CERTIFICATE = config_mgr.get('synology.certificate', 'SYNO_CERTIFICATE', '')
SYNO_CREATE = config_mgr.get('synology.create', 'SYNO_CREATE', '1')


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
            'SYNO_USERNAME': SYNO_USERNAME,
            'SYNO_PASSWORD': SYNO_PASSWORD,
            'SYNO_HOSTNAME': SYNO_HOSTNAME,
            'SYNO_PORT': SYNO_PORT,
            'SYNO_SCHEME': SYNO_SCHEME
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
    logging.info(f"开始为域名 *.{DOMAIN} 和 {DOMAIN} 申请/续签证书...")
    acme_sh_path = '/root/.acme.sh/acme.sh'
    
    issue_command = [
        acme_sh_path, '--issue', '--dns', DNS_API,
        '-d', DOMAIN, '-d', f'*.{DOMAIN}',
        '--keylength', 'ec-256', '--log'
    ]

    # 动态准备需要传递给 acme.sh 的环境变量。
    # 这会自动抓取所有相关的 DNS 提供商的环境变量，例如 DP_Id, DP_Key, CF_Token 等。
    dns_api_prefixes = ('DP_', 'CF_', 'ALI_', 'GD_', 'HE_', 'CLOUDXNS_', 'GODADDY_')
    command_env = {k: v for k, v in os.environ.items() if k.startswith(dns_api_prefixes)}

    success, output = run_command(issue_command, env_vars=command_env)
    
    if not success:
        error_message = f"证书申请/续签失败。错误详情: \n{output}"
        logging.error(error_message)
        return False, output
    
    logging.info("证书申请/续签命令执行成功。")
    return True, ""


def deploy_to_synology():
    """将证书部署到 Synology DSM"""
    if not AUTO_DEPLOY_TO_SYNOLOGY:
        return True, ""
        
    logging.info("开始将证书部署到 Synology DSM...")
    acme_sh_path = '/root/.acme.sh/acme.sh'
    
    deploy_command = [
        acme_sh_path, '--deploy',
        '-d', DOMAIN,
        '--deploy-hook', 'synology_dsm'
    ]
    
    # 准备群晖部署所需的环境变量
    deploy_env = {
        'SYNO_USERNAME': SYNO_USERNAME,
        'SYNO_PASSWORD': SYNO_PASSWORD,
        'SYNO_HOSTNAME': SYNO_HOSTNAME,
        'SYNO_PORT': str(SYNO_PORT),
        'SYNO_SCHEME': SYNO_SCHEME,
        'SYNO_CERTIFICATE': SYNO_CERTIFICATE,
        'SYNO_CREATE': str(SYNO_CREATE)
    }
    
    logging.info(f"部署参数: 主机={SYNO_HOSTNAME}:{SYNO_PORT}, 协议={SYNO_SCHEME}, 创建新证书={SYNO_CREATE}")
    
    success, output = run_command(deploy_command, env_vars=deploy_env)
    
    if not success:
        error_message = f"部署到 Synology DSM 失败。错误详情: \n{output}"
        logging.error(error_message)
        return False, error_message
    
    logging.info("证书已成功部署到 Synology DSM。")
    return True, ""


def validate_cert_files(output_path=None):
    """验证生成的证书文件是否符合群晖要求"""
    if output_path is None:
        output_path = CERT_OUTPUT_PATH
    
    privkey_path = os.path.join(output_path, 'privkey.pem')
    cert_path = os.path.join(output_path, 'cert.pem')
    ca_path = os.path.join(output_path, 'chain.pem')
    
    errors = []
    
    # 检查文件是否存在
    for file_path, file_type in [(privkey_path, '私钥'), (cert_path, '证书'), (ca_path, '中间证书')]:
        if not os.path.exists(file_path):
            errors.append(f"{file_type}文件不存在: {file_path}")
            continue
            
        # 检查文件是否为空
        if os.path.getsize(file_path) == 0:
            errors.append(f"{file_type}文件为空: {file_path}")
            continue
            
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # 检查 PEM 格式
            if file_type == '私钥':
                if not ('-----BEGIN PRIVATE KEY-----' in content or '-----BEGIN EC PRIVATE KEY-----' in content or '-----BEGIN RSA PRIVATE KEY-----' in content):
                    errors.append(f"{file_type}文件格式不正确，应为 PEM 格式")
                # 检查私钥是否有密码保护（简单检查）
                if 'ENCRYPTED' in content.upper():
                    errors.append(f"{file_type}文件不能有密码保护")
            else:
                if not ('-----BEGIN CERTIFICATE-----' in content and '-----END CERTIFICATE-----' in content):
                    errors.append(f"{file_type}文件格式不正确，应为 X.509 PEM 格式")
                    
        except Exception as e:
            errors.append(f"读取{file_type}文件时出错: {e}")
    
    if errors:
        return False, "; ".join(errors)
    
    logging.info("证书文件验证通过，符合群晖要求")
    return True, ""


def install_cert():
    """将生成的证书文件拷贝到指定的输出目录，生成群晖所需的三个独立文件"""
    logging.info(f"开始将证书安装到输出目录: {CERT_OUTPUT_PATH}")
    acme_sh_path = '/root/.acme.sh/acme.sh'
    
    try:
        os.makedirs(CERT_OUTPUT_PATH, exist_ok=True)
    except OSError as e:
        error_msg = f"创建输出目录 {CERT_OUTPUT_PATH} 失败: {e}"
        logging.error(error_msg)
        return False, error_msg

    # 群晖需要的三个文件路径
    privkey_path = os.path.join(CERT_OUTPUT_PATH, 'privkey.pem')      # 私钥文件
    cert_path = os.path.join(CERT_OUTPUT_PATH, 'cert.pem')           # 证书文件（不包含中间证书）
    ca_path = os.path.join(CERT_OUTPUT_PATH, 'chain.pem')            # 中间证书文件
    fullchain_path = os.path.join(CERT_OUTPUT_PATH, 'fullchain.pem') # 完整证书链（备用）

    install_command = [
        acme_sh_path, '--install-cert',
        '-d', DOMAIN,
        '--key-file', privkey_path,        # 私钥文件
        '--cert-file', cert_path,          # 证书文件（仅包含域名证书）
        '--ca-file', ca_path,              # 中间证书文件
        '--fullchain-file', fullchain_path, # 完整证书链（备用）
        '--reloadcmd', 'echo "Certificate installed."'
    ]

    success, error_output = run_command(install_command)
    if not success:
        error_message = f"将证书文件安装到 {CERT_OUTPUT_PATH} 失败: {error_output}"
        logging.error(error_message)
        return False, error_message

    # 验证生成的文件是否符合群晖要求
    validation_success, validation_error = validate_cert_files()
    if not validation_success:
        logging.warning(f"证书文件验证警告: {validation_error}")

    logging.info(f"证书已成功安装到 {CERT_OUTPUT_PATH}")
    logging.info("群晖所需的证书文件:")
    logging.info(f"  私钥文件: {privkey_path}")
    logging.info(f"  证书文件: {cert_path}")
    logging.info(f"  中间证书: {ca_path}")
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
        # 部署到群晖（如果启用）
        deploy_success, deploy_error = deploy_to_synology()
        
        # 安装证书文件到输出目录
        install_success, install_error = install_cert()
        
        if install_success:
            success_details = f"证书已成功续签并保存到 {CERT_OUTPUT_PATH}。\n"
            success_details += "生成的群晖证书文件:\n"
            success_details += "  • privkey.pem (私钥文件)\n"
            success_details += "  • cert.pem (证书文件)\n"
            success_details += "  • chain.pem (中间证书)\n"
            success_details += "  • fullchain.pem (完整证书链，备用)"
            
            if AUTO_DEPLOY_TO_SYNOLOGY:
                if deploy_success:
                    success_details += "\n\n✅ 已成功自动部署到 Synology DSM。"
                else:
                    success_details += f"\n\n❌ 自动部署到 Synology DSM 失败: {deploy_error}"
                    
            logging.info("--- 证书自动化任务成功完成 ---")
            notification_mgr.dispatch("success", DOMAIN, details=success_details)
        else:
            warning_details = f"证书续签成功，但保存证书到 {CERT_OUTPUT_PATH} 失败: {install_error}"
            if AUTO_DEPLOY_TO_SYNOLOGY:
                if deploy_success:
                    warning_details += "\n✅ 已成功部署到 Synology DSM。"
                else:
                    warning_details += f"\n❌ 部署到 Synology DSM 失败: {deploy_error}"
            logging.warning(warning_details)
            notification_mgr.dispatch("success", DOMAIN, details=warning_details)
    else:
        logging.error("--- 证书自动化任务失败 ---")
        notification_mgr.dispatch("failure", DOMAIN, details=issue_error)

