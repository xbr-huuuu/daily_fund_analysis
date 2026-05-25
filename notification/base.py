"""通知渠道抽象基类"""

from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    """通知渠道抽象基类"""

    @abstractmethod
    async def send(self, title: str, content: str) -> bool:
        """发送通知，返回是否成功"""
        ...
