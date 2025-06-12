import os
import json
import logging
import requests
import time
from datetime import datetime
from .base_notifier import BaseNotifier

class WecomAppNotifier(BaseNotifier):
    """
    企业微信内部应用通知的实现类。
    """
    def __init__(self):
        self.corp_id = None # 默认为 None，表示禁用
        config = self._load_config()
        wecom_config = config.get('notifiers', {}).get('wecom', {})

        # 从环境变量或配置文件加载配置 (环境变量优先)
        self.corp_id = os.environ.get('CORP_ID') or wecom_config.get('corp_id')
        self.corp_secret = os.environ.get('CORP_SECRET') or wecom_config.get('corp_secret')
        self.agent_id = os.environ.get('AGENT_ID') or wecom_config.get('agent_id')
        self.to_user = os.environ.get('TO_USER') or wecom_config.get('to_user') or "@all"
        
        self._access_token = None
        self._token_expires_at = 0

        if self.corp_id and self.corp_secret and self.agent_id:
            logging.info("已加载企业微信应用通知配置。")
        else:
            self.corp_id = None # 确保配置不完整时禁用

    def _load_config(self):
        """从标准路径加载配置文件"""
        try:
            with open('/config/config.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # 如果文件不存在或无效，返回空字典
            return {}

    def _get_access_token(self):
        """获取或刷新 access_token"""
        if self._token_expires_at > time.time() and self._access_token:
            return self._access_token

        logging.info("正在获取新的 access_token...")
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {"corpid": self.corp_id, "corpsecret": self.corp_secret}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("errcode") == 0:
                self._access_token = data.get("access_token")
                self._token_expires_at = time.time() + 7000
                logging.info("成功获取 access_token。")
                return self._access_token
            else:
                logging.error(f"获取 access_token 失败: {data.get('errmsg')}")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"获取 access_token 时发生网络错误: {e}")
            return None

    def send(self, status: str, domain: str, details: str = ""):
        # (此方法内容保持不变, 这里省略以保持简洁)
        if not self.corp_id:
            return

        access_token = self._get_access_token()
        if not access_token:
            logging.error("无法发送通知，因为获取 access_token 失败。")
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if status == "success":
            title = f"✅ 证书续签成功: {domain}"
            description = f"<div class=\"gray\">{now_str}</div><div class=\"normal\">域名 {domain} 的泛域名证书已成功续签并部署！</div>"
        else:
            title = f"❌ 证书续签失败: {domain}"
            description = f"<div class=\"gray\">{now_str}</div><div class=\"highlight\">域名 {domain} 证书续签失败，请检查容器日志。</div>"

        payload = {
            "touser": self.to_user,
            "msgtype": "textcard",
            "agentid": int(self.agent_id),
            "textcard": {
                "title": title,
                "description": description,
                "url": "https://github.com/acmesh-official/acme.sh",
                "btntxt": "了解更多"
            },
            "enable_id_trans": 0
        }

        send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        try:
            logging.info("正在发送企业微信应用通知...")
            response = requests.post(send_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("errcode") == 0:
                logging.info("企业微信应用通知发送成功。")
            else:
                logging.error(f"企业微信应用通知发送失败: {result}")
        except requests.exceptions.RequestException as e:
            logging.error(f"发送企业微信应用通知时发生网络错误: {e}")

