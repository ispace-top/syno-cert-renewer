from abc import ABC, abstractmethod

class BaseNotifier(ABC):
    """
    所有通知服务的抽象基类。
    每个具体的通知器都必须实现 'send' 方法。
    """
    @abstractmethod
    def send(self, status: str, domain: str, details: str = "") -> None:
        """
        发送通知的抽象方法。

        :param status: 操作状态 ('success' 或 'failure').
        :param domain: 操作涉及的域名。
        :param details: 关于结果的可选额外信息。
        """
        pass
