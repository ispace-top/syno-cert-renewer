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
    它通过 CorpID 和 CorpSecret 获取 access_token 来发送消息。
    """
    def __init__(self):
        # 加载默认配置
        config = self._load_config()
        wecom_config = config.get('notifiers', {}).get('wecom', {})

        # 从环境变量加载配置 (优先级更高)
        self.corp_id = os.environ.get('CORP_ID') or wecom_config.get('corp_id')
        self.corp_secret = os.environ.get('CORP_SECRET') or wecom_config.get('corp_secret')
        self.agent_id = os.environ.get('AGENT_ID') or wecom_config.get('agent_id')
        self.to_user = os.environ.get('TO_USER') or wecom_config.get('to_user') or "@all"
        
        # 内部状态
        self._access_token = None
        self._token_expires_at = 0

        # 检查配置是否完整
        if self.corp_id and self.corp_secret and self.agent_id:
            logging.info("已加载企业微信应用通知配置。")
        else:
            # 配置不完整则禁用此通知器
            self.corp_id = None

    def _load_config(self):
        try:
            with open('/app/src/config/config.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _get_access_token(self):
        """
        获取或刷新 access_token，并进行内存缓存。
        """
        # 如果缓存中的 token 有效，则直接返回
        if self._token_expires_at > time.time() and self._access_token:
            logging.info("使用缓存的 access_token。")
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
                # Token 有效期为 7200s，我们提前 200s 让其失效
                self._token_expires_at = time.time() + 7000
                logging.info("成功获取 access_token。")
                return self._access_token
            else:
                logging.error(f"获取 access_token 失败: {data.get('errmsg')}")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"获取 access_token 时发生网络错误: {e}")
            return None

    def send(self, status: str, domain: str, details: str = "") -> None:
        if not self.corp_id:
            return # 配置不完整，不发送

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

        # 使用更美观的 textcard 消息格式
        payload = {
            "touser": self.to_user,
            "msgtype": "textcard",
            "agentid": int(self.agent_id),
            "textcard": {
                "title": title,
                "description": description,
                "url": "https://github.com/acmesh-official/acme.sh", # URL 是必填项, 指向 acme.sh 项目
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
