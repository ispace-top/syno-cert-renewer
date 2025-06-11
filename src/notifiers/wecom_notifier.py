import os
import json
import logging
import requests
from datetime import datetime
from .base_notifier import BaseNotifier

class WecomNotifier(BaseNotifier):
    """
    企业微信 (WeCom) 的通知实现类。
    """
    def __init__(self):
        self.webhook_url = None
        config_url = None
        
        # 1. 尝试从配置文件加载 URL
        try:
            with open('/app/src/config/config.json', 'r') as f:
                # !!! 关键修复：将文件对象 f 传递给 json.load() !!!
                config = json.load(f)
            config_url = config.get('notifiers', {}).get('wecom', {}).get('webhook_url')
        except (FileNotFoundError, json.JSONDecodeError):
            # 配置文件不存在或格式错误，静默处理
            pass

        # 2. 检查环境变量，其优先级更高
        env_url = os.environ.get('WECOM_WEBHOOK_URL')

        # 决定最终使用的 URL
        self.webhook_url = env_url or config_url
        if self.webhook_url:
             logging.info("已加载企业微信 Webhook 配置。")

    def send(self, status: str, domain: str, details: str = "") -> None:
        if not self.webhook_url:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if status == "success":
            title = "✅ 证书续签成功"
            color = "info"
            description = f"域名 **{domain}** 的泛域名证书已成功续签并部署！"
        else:
            title = "❌ 证书续签失败"
            color = "warning"
            description = f"域名 **{domain}** 的证书续签失败，请检查容器日志。"

        message_content = f"""# {title}
> 域名: <font color=\"info\">{domain}</font>
> 时间: <font color=\"comment\">{now}</font>
> 状态: <font color=\"{color}\">{description}</font>
"""
        if details:
            cleaned_details = str(details).replace("\n", " ").strip()
            message_content += f"> 详情: <font color=\"comment\">{cleaned_details}</font>"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": message_content
            }
        }
        
        try:
            logging.info("正在发送企业微信通知...")
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("errcode") == 0:
                logging.info("企业微信通知发送成功。")
            else:
                logging.error(f"企业微信通知发送失败: {result.get('errmsg')}")
        except requests.exceptions.RequestException as e:
            logging.error(f"发送企业微信通知时发生网络错误: {e}")
