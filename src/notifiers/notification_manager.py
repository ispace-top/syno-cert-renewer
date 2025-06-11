import logging
from .wecom_notifier import WecomNotifier

# 未来可以在这里导入其他通知服务的实现
# from .dingtalk_notifier import DingTalkNotifier
# from .email_notifier import EmailNotifier

class NotificationManager:
    def __init__(self):
        self.notifiers = []
        self._discover_notifiers()

    def _discover_notifiers(self):
        """
        初始化并添加所有可用的通知器。
        未来可以使这个过程更加动态化。
        """
        # 添加企业微信通知器
        self.notifiers.append(WecomNotifier())
        
        # 当其他通知器实现后，在此处添加
        # self.notifiers.append(DingTalkNotifier())
        # self.notifiers.append(EmailNotifier())
        
        logging.info(f"已加载 {len(self.notifiers)} 个通知服务。")

    def dispatch(self, status: str, domain: str, details: str = ""):
        """
        将通知分发到所有已注册的通知器。
        """
        if not self.notifiers:
            logging.info("没有配置任何通知服务，跳过发送。")
            return
            
        logging.info(f"正在向所有已配置的服务分发 '{status}' 通知...")
        for notifier in self.notifiers:
            try:
                # 调用每个通知器实例的 send 方法
                notifier.send(status, domain, details)
            except Exception as e:
                # 记录错误但不要中断主程序
                logging.error(f"发送通知时发生错误 ({type(notifier).__name__}): {e}", exc_info=True)
