import os
import sys
import logging
import subprocess
import time
import json
from datetime import datetime, timedelta
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
DOMAIN = str(config_mgr.get('general.domain', 'DOMAIN') or '')
DNS_API = str(config_mgr.get('general.dns_api', 'DNS_API') or '')
ACME_EMAIL = str(config_mgr.get('general.acme_email', 'ACME_EMAIL') or '')
CERT_OUTPUT_PATH = str(config_mgr.get('general.cert_output_path', 'CERT_OUTPUT_PATH', '/output') or '/output')
RENEW_DAYS_BEFORE_EXPIRY = int(str(config_mgr.get('general.renew_days_before_expiry', 'RENEW_DAYS_BEFORE_EXPIRY', 30) or '30'))

# Synology 部署配置
AUTO_DEPLOY_TO_SYNOLOGY = config_mgr.get('synology.auto_deploy', 'AUTO_DEPLOY_TO_SYNOLOGY', False)
SYNO_USERNAME = str(config_mgr.get('synology.username', 'SYNO_USERNAME') or '')
SYNO_PASSWORD = str(config_mgr.get('synology.password', 'SYNO_PASSWORD') or '')
SYNO_PORT = str(config_mgr.get('synology.port', 'SYNO_PORT') or '')
SYNO_SCHEME = str(config_mgr.get('synology.scheme', 'SYNO_SCHEME') or '')
SYNO_HOSTNAME = str(config_mgr.get('synology.hostname', 'SYNO_HOSTNAME') or '')
SYNO_CERTIFICATE = str(config_mgr.get('synology.certificate', 'SYNO_CERTIFICATE', '') or '')
SYNO_CREATE = str(config_mgr.get('synology.create', 'SYNO_CREATE', '1') or '1')

# 状态文件路径
STATE_FILE_PATH = '/app/.last_run'
SCHEDULER_STATE_FILE_PATH = '/app/.scheduler_state'


# 初始化通知管理器
notification_mgr = NotificationManager()


def needs_renewal(domain: str, days_before_expiry: int) -> tuple:
    """
    通过 OpenSSL 检查域名的 SSL 证书是否需要续签。

    :param domain: 要检查的域名。
    :param days_before_expiry: 在证书过期前多少天应判断为需要续签。
    :return: (bool, datetime) 如果需要续签，返回 True 和证书过期时间，否则返回 False 和证书过期时间。
    """
    logging.info(f"开始检查域名 '{domain}' 的证书状态...")

    try:
        # 使用 openssl s_client 获取证书信息
        command = f"echo | openssl s_client -connect {domain}:443 -servername {domain} 2>/dev/null | openssl x509 -noout -enddate"

        process = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            timeout=15  # 15秒超时
        )

        output = process.stdout.strip()

        if not output.startswith('notAfter='):
            logging.warning(f"无法从命令输出中解析有效期: {output}")
            logging.info("将默认需要续签以确保安全。")
            return True, None

        # 解析日期
        expiry_date_str = output.split('=', 1)[1]
        # OpenSSL 日期格式: "Month Day HH:MM:SS YYYY GMT"
        expiry_date = datetime.strptime(expiry_date_str, '%b %d %H:%M:%S %Y %Z')

        time_left = expiry_date - datetime.utcnow()

        logging.info(f"域名 '{domain}' 的证书将于 {time_left.days} 天后过期 (在 {expiry_date.strftime('%Y-%m-%d')} 到期)。")

        if time_left < timedelta(days=days_before_expiry):
            logging.info(f"证书剩余时间小于阈值 {days_before_expiry} 天，需要续签。")
            return True, expiry_date
        else:
            logging.info(f"证书有效期尚足，无需续签。")
            return False, expiry_date

    except subprocess.TimeoutExpired:
        logging.warning(f"检查证书时连接到 '{domain}:443' 超时。")
        logging.info("将默认需要续签以确保可用性。")
        return True, None
    except subprocess.CalledProcessError as e:
        logging.warning(f"使用 OpenSSL 检查证书失败: {e.stderr}")
        logging.info("可能是域名不存在、未部署证书或网络问题。将默认需要续签。")
        return True, None
    except Exception as e:
        logging.error(f"检查证书时发生未知错误: {e}")
        logging.info("将默认需要续签以确保安全。")
        return True, None


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


def save_scheduler_state(next_run_time):
    """保存调度器状态（下次运行时间）"""
    try:
        with open(SCHEDULER_STATE_FILE_PATH, 'w') as f:
            json.dump({
                'next_run_time': next_run_time.isoformat()
            }, f)
    except Exception as e:
        logging.warning(f"无法保存调度器状态: {e}")


if __name__ == "__main__":
    logging.info("--- Synology 证书续签工具启动 ---")

    validate_config()

    # 检查证书是否需要续签
    need_renew, expiry_date = needs_renewal(DOMAIN, RENEW_DAYS_BEFORE_EXPIRY)
            
    if not need_renew:
        logging.info("--- 证书检查完成，无需操作 ---")
        # 计算下次运行时间
        next_run_time = datetime.now() + timedelta(days=config_mgr.cert_check_interval_days)
        if expiry_date:
            # 根据证书过期时间计算下次运行时间，确保证书过期前 renew
            suggested_next_run = expiry_date - timedelta(days=RENEW_DAYS_BEFORE_EXPIRY - 1)
            next_run_time = min(next_run_time, suggested_next_run)
                
        # 发送成功通知，包含完整的任务信息
        success_details = f"✅ 证书续签检查完成\n\n域名: {DOMAIN}\n状态: SUCCESS\n事件: 证书有效期尚足，无需续签\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n下次计划运行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}"
                
        # 更新状态文件
        with open(STATE_FILE_PATH, 'w') as f:
            json.dump({
                'last_run': datetime.now().isoformat(),
                'expiry_date': expiry_date.isoformat() if expiry_date else None,
                'need_renew': False
            }, f)
                
        # 发送合并后的成功通知
        notification_mgr.dispatch(
            "success",
            DOMAIN,
            details=success_details
        )
                
        # 保存调度器状态供主循环使用
        save_scheduler_state(next_run_time)
        sys.exit(0)

    # -- 如果需要续签，则执行以下流程 --
    logging.info("证书需要续签，开始执行 acme.sh 流程...")

    if not setup_acme_account():
        error_msg = "acme.sh 账户设置失败，程序终止。"
        logging.error(error_msg)
        
        # 计算下次运行时间
        next_run_time = datetime.now() + timedelta(days=config_mgr.cert_check_interval_days)
        
        # 发送失败通知，包含完整的任务信息
        failure_details = f"❌ 证书续签失败\n\n域名: {DOMAIN}\n状态: FAILURE\n事件: acme.sh 账户设置失败\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n原因: {error_msg}\n下次计划运行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 更新状态文件
        with open(STATE_FILE_PATH, 'w') as f:
            json.dump({
                'last_run': datetime.now().isoformat(),
                'expiry_date': expiry_date.isoformat() if expiry_date else None,
                'need_renew': False
            }, f)
        
        # 发送失败通知
        notification_mgr.dispatch(
            "failure",
            DOMAIN,
            details=failure_details
        )
        
        # 保存调度器状态供主循环使用
        save_scheduler_state(next_run_time)
        sys.exit(1)

    issue_success, issue_error = issue_or_renew_cert()

    if issue_success:
        # 部署到群晖（如果启用）
        deploy_success, deploy_error = deploy_to_synology()

        # 安装证书文件到输出目录
        install_success, install_error = install_cert()

        # 构建最终通知消息
        final_details = f"✅ 证书续签成功\n\n域名: {DOMAIN}\n状态: SUCCESS\n"
        final_details += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        final_details += f"证书保存位置: {CERT_OUTPUT_PATH}\n"
        final_details += "生成的群晖证书文件:\n"
        final_details += "  • privkey.pem (私钥文件)\n"
        final_details += "  • cert.pem (证书文件)\n"
        final_details += "  • chain.pem (中间证书)\n"
        final_details += "  • fullchain.pem (完整证书链，备用)\n\n"
        
        if AUTO_DEPLOY_TO_SYNOLOGY:
            if deploy_success:
                final_details += "✅ 已成功自动部署到 Synology DSM。\n\n"
            else:
                final_details += f"❌ 自动部署到 Synology DSM 失败: {deploy_error}\n\n"

        # 计算下次运行时间
        next_run_time = datetime.now() + timedelta(days=config_mgr.cert_check_interval_days)
        # 获取新证书的过期时间
        _, new_expiry_date = needs_renewal(DOMAIN, RENEW_DAYS_BEFORE_EXPIRY)
        if new_expiry_date:
            # 根据新证书过期时间计算下次运行时间
            suggested_next_run = new_expiry_date - timedelta(days=RENEW_DAYS_BEFORE_EXPIRY - 1)
            next_run_time = min(next_run_time, suggested_next_run)
        
        final_details += f"下次计划运行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 更新状态文件
        with open(STATE_FILE_PATH, 'w') as f:
            json.dump({
                'last_run': datetime.now().isoformat(),
                'expiry_date': new_expiry_date.isoformat() if new_expiry_date else None,
                'need_renew': False
            }, f)
        
        logging.info("--- 证书自动化任务成功完成 ---")
        notification_mgr.dispatch("success", DOMAIN, details=final_details)
        
        # 保存调度器状态供主循环使用
        save_scheduler_state(next_run_time)
    else:
        logging.error("--- 证书自动化任务失败 ---")
        
        # 为速率限制错误创建用户友好的消息
        if "urn:ietf:params:acme:error:rateLimited" in issue_error or "too many certificates" in issue_error:
            user_friendly_error = (
                "证书申请失败：达到 Let's Encrypt 的速率限制。\n\n"
                "原因: 这通常是因为在短时间内重复申请了太多次新证书。最常见的原因是 Docker 容器没有持久化 `/root/.acme.sh` 目录，导致每次重启都像初次运行一样申请新证书。\n\n"
                "解决方案:\n"
                "1. 检查并添加卷挂载: 请确保您的 `docker-compose.yml` 文件中包含了以下这行，以持久化 `acme.sh` 的状态：\n"
                "   volumes:\n"
                "     - ./acme.sh:/root/.acme.sh\n"
                "2. 等待限制解除: 您需要等待速率限制解除后才能再次成功申请。请查看以下原始错误日志中的 retry after 时间点。\n\n"
                f"原始错误详情:\n{issue_error}"
            )
            
            # 对于速率限制等可恢复错误，设置较短的重试时间
            next_run_time = datetime.now() + timedelta(hours=1)  # 1小时后重试
            
            failure_details = f"❌ 证书续签失败\n\n域名: {DOMAIN}\n状态: FAILURE\n"
            failure_details += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            failure_details += f"原因: {user_friendly_error}\n"
            failure_details += f"下次计划运行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}"
            
            notification_mgr.dispatch("failure", DOMAIN, details=failure_details)
        else:
            # 对于所有其他错误，发送原始错误
            # 对于其他错误，按常规间隔再次运行
            next_run_time = datetime.now() + timedelta(days=config_mgr.cert_check_interval_days)
            
            failure_details = f"❌ 证书续签失败\n\n域名: {DOMAIN}\n状态: FAILURE\n"
            failure_details += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            failure_details += f"原因: {issue_error}\n"
            failure_details += f"下次计划运行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}"
            
            notification_mgr.dispatch("failure", DOMAIN, details=failure_details)
        
        # 保存调度器状态供主循环使用
        save_scheduler_state(next_run_time)
