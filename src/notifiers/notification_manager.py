import logging
from .wecom_notifier import WeComNotifier

class NotificationManager:
    def __init__(self):
        self.notifiers = []
        self._discover_notifiers()

    def _discover_notifiers(self):
        """
        初始化并添加所有可用的通知器。
        """
        # 添加企业微信应用通知器
        self.notifiers.append(WecomAppNotifier())
        
        logging.info(f"已加载 {len(self.notifiers)} 个通知服务。")

    def dispatch(self, status: str, domain: str, details: str = ""):
        """
        将通知分发到所有已注册的通知器。
        """
        if not any(n.corp_id for n in self.notifiers if isinstance(n, WecomAppNotifier)): # 示例检查
             logging.info("没有配置任何有效的通知服务，跳过发送。")
             return
            
        logging.info(f"正在向所有已配置的服务分发 '{status}' 通知...")
        for notifier in self.notifiers:
            try:
                notifier.send(status, domain, details)
            except Exception as e:
                logging.error(f"发送通知时发生错误 ({type(notifier).__name__}): {e}", exc_info=True)
