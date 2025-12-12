import os
import json
import time
import requests
import logging
from .base_notifier import BaseNotifier
from config_manager import ConfigManager

class WeComNotifier(BaseNotifier):
    """
    通过企业微信应用发送纯文本格式消息的通知器。
    这种方式可以确保在微信插件中也能正常显示。
    """
    def __init__(self):
        config_mgr = ConfigManager()
        self.corp_id = config_mgr.get("notifiers.wecom.corp_id", "WECOM_CORP_ID")
        self.corp_secret = config_mgr.get("notifiers.wecom.corp_secret", "WECOM_CORP_SECRET")
        self.agent_id = config_mgr.get("notifiers.wecom.agent_id", "WECOM_AGENT_ID")
        self.touser = config_mgr.get("notifiers.wecom.touser", "WECOM_TOUSER", "@all")

        self.api_origin = "https://qyapi.weixin.qq.com"
        self.token_cache_path = "/temp/wecom_token.json"
        self.access_token = None
        self.token_expires_at = 0

    def _get_access_token(self):
        """高效地获取并缓存 access_token。"""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token

        try:
            if os.path.exists(self.token_cache_path):
                with open(self.token_cache_path, "r") as f:
                    cache = json.load(f)
                    if time.time() < cache.get("expires_at", 0):
                        self.access_token = cache.get("access_token")
                        self.token_expires_at = cache.get("expires_at")
                        logging.info("从文件缓存加载了有效的 access_token。")
                        return self.access_token
        except (IOError, json.JSONDecodeError) as e:
            logging.warning(f"读取 token 缓存文件失败: {e}，将重新获取。")

        logging.info("access_token 无效或已过期，正在从企业微信 API 获取新的 token...")
        if not all([self.corp_id, self.corp_secret]):
            logging.error("获取 access_token 失败: corp_id 或 corp_secret 未配置。")
            return None
            
        url = f"{self.api_origin}/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("errcode") == 0:
                self.access_token = data.get("access_token")
                self.token_expires_at = time.time() + data.get("expires_in", 7200) - 200
                try:
                    with open(self.token_cache_path, "w") as f:
                        json.dump({"access_token": self.access_token, "expires_at": self.token_expires_at}, f)
                    logging.info("成功获取并缓存了新的 access_token。")
                except IOError as e:
                    logging.warning(f"写入 token 缓存文件失败: {e}")
                return self.access_token
            else:
                logging.error(f"获取 access_token 失败: {data.get('errmsg')} (errcode: {data.get('errcode')})")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"请求 access_token 时发生网络错误: {e}")
            return None

    def send(self, status, domain, details=""):
        """主发送方法，被 NotificationManager 调用。"""
        if not all([self.corp_id, self.corp_secret, self.agent_id]):
            logging.warning("企业微信通知缺少必要的参数 (corp_id, corp_secret, agent_id)，跳过发送。")
            return

        token = self._get_access_token()
        if not token:
            logging.error("无法发送消息，因为 access_token 获取失败。")
            return

        # 准备纯文本内容
        text_content = details if details else (
            f"{'✅ 证书续签成功' if status == 'success' else '❌ 证书续签失败'}\n"
            f"域名: {domain}\n"
            f"状态: {status.upper()}\n"
        )

        send_url = f"{self.api_origin}/cgi-bin/message/send?access_token={token}"
        # 将 payload 修改为 text 类型
        payload = {
            "touser": self.touser,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": text_content
            },
            "safe": 0,
            "enable_id_trans": 0,
            "enable_duplicate_check": 0,
            "duplicate_check_interval": 1800
        }

        # --- 修改结束 ---

        try:
            response = requests.post(send_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("errcode") == 0:
                logging.info("企业微信 text 消息发送成功。")
            else:
                logging.error(f"企业微信 text 消息发送失败: {result.get('errmsg')} (errcode: {result.get('errcode')})")
        except requests.exceptions.RequestException as e:
            logging.error(f"发送企业微信 text 消息时发生网络错误: {e}")