import os
import json
import time
import requests
import logging
from .base_notifier import BaseNotifier
from config_manager import ConfigManager

class WeComNotifier(BaseNotifier):
    def __init__(self):
        config_mgr = ConfigManager()
        # 从配置或环境变量中加载企业微信参数
        self.corp_id = config_mgr.get('notifiers.wecom.corp_id', 'WECOM_CORP_ID')
        self.corp_secret = config_mgr.get('notifiers.wecom.corp_secret', 'WECOM_CORP_SECRET')
        self.agent_id = config_mgr.get('notifiers.wecom.agent_id', 'WECOM_AGENT_ID')
        self.touser = config_mgr.get('notifiers.wecom.touser', 'WECOM_TOUSER', '@all')
        
        self.token_cache_path = '/temp/wecom_token.json'
        self.access_token = None
        self.token_expires_at = 0

    def _get_access_token(self):
        """获取并缓存 access_token"""
        # 检查内存中的 token 是否有效
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token

        # 检查文件缓存中的 token
        try:
            with open(self.token_cache_path, 'r') as f:
                cache = json.load(f)
                if time.time() < cache.get('expires_at', 0):
                    self.access_token = cache.get('access_token')
                    self.token_expires_at = cache.get('expires_at')
                    logging.info("从文件缓存加载了有效的 access_token。")
                    return self.access_token
        except (FileNotFoundError, json.JSONDecodeError):
            pass # 缓存不存在或无效

        # 如果缓存都无效，则从 API 获取新 token
        logging.info("access_token 无效或已过期，正在获取新的 token...")
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("errcode") == 0:
                self.access_token = data.get("access_token")
                # 提前 200 秒过期，留出网络延迟等余地
                self.token_expires_at = time.time() + data.get("expires_in", 7200) - 200
                # 写入文件缓存
                with open(self.token_cache_path, 'w') as f:
                    json.dump({'access_token': self.access_token, 'expires_at': self.token_expires_at}, f)
                logging.info("成功获取并缓存了新的 access_token。")
                return self.access_token
            else:
                logging.error(f"获取 access_token 失败: {data.get('errmsg')}")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"请求 access_token 时发生网络错误: {e}")
            return None

    def send(self, status, domain, details=""):
        # 检查是否配置了必要的参数
        if not all([self.corp_id, self.corp_secret, self.agent_id]):
            logging.warning("企业微信通知缺少必要的参数 (corp_id, corp_secret, agent_id)，跳过发送。")
            return

        token = self._get_access_token()
        if not token:
            logging.error("无法获取 access_token，通知发送失败。")
            return

        if status == "success":
            title = f"✅ 证书续签成功: {domain}"
            color = "info"  # 绿色
        else:
            title = f"❌ 证书续签失败: {domain}"
            color = "warning"  # 红色

        # 详情内容中的换行符需要处理
        details_md = details.replace('\n', '\n>')

        content = f"""
        > **{title}**
        > **状态**: <font color=\"{color}\">{status.upper()}</font>
        > **详情**: {details_md if details else 'N/A'}
        """

        send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        payload = {
            "touser": self.touser,
            "msgtype": "markdown",
            "agentid": self.agent_id,
            "markdown": {
                "content": content.strip()
            }
        }

        try:
            response = requests.post(send_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("errcode") == 0:
                logging.info("企业微信通知发送成功。")
            else:
                logging.error(f"企业微信通知发送失败: {result.get('errmsg')}")
        except requests.exceptions.RequestException as e:
            logging.error(f"发送企业微信通知时发生网络错误: {e}")

