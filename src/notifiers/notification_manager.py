from .wecom_notifier import WeComNotifier

class NotificationManager:
    def __init__(self):
        """
        初始化通知管理器并加载所有可用的通知器。
        """
        self.notifiers = []
        # 在这里可以添加更多的通知器
        # 我们现在正确地实例化 WeComNotifier 类
        self.notifiers.append(WeComNotifier())

    def dispatch(self, status, domain, details=""):
        """
        分发通知到所有已注册的通知器。
        """
        if not self.notifiers:
            print("没有配置任何通知器。")
            return

        print(f"正在向 {len(self.notifiers)} 个通知器分发消息...")
        for notifier in self.notifiers:
            try:
                # 调用每个通知器实例的 send 方法
                notifier.send(status, domain, details)
            except Exception as e:
                # 增加错误捕获，防止一个通知器的失败影响其他通知器
                print(f"发送通知时遇到错误: {e}")

