"""通知管理器 - 多渠道分发"""

import asyncio
import logging

from config.settings import Settings
from notification.base import BaseNotifier
from notification.channels.wechat_work import WechatWorkNotifier
from notification.channels.telegram import TelegramNotifier
from notification.channels.email_notifier import EmailNotifier
from notification.channels.feishu import FeishuNotifier

logger = logging.getLogger(__name__)


class NotificationManager:
    """通知管理器，支持多渠道并发推送"""

    def __init__(self, notifiers: list[BaseNotifier]):
        self.notifiers = notifiers

    @classmethod
    def from_config(cls, config: Settings) -> "NotificationManager":
        """从配置创建通知管理器"""
        notifiers: list[BaseNotifier] = []

        if not config.notify_enabled:
            logger.info("通知功能已禁用")
            return cls(notifiers)

        # 企业微信
        if config.wechat_webhook_url:
            notifiers.append(WechatWorkNotifier(config.wechat_webhook_url))
            logger.info("已启用企业微信通知")

        # 飞书
        if config.feishu_webhook_url:
            notifiers.append(FeishuNotifier(config.feishu_webhook_url))
            logger.info("已启用飞书通知")

        # Telegram
        if config.telegram_bot_token and config.telegram_chat_id:
            notifiers.append(TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id))
            logger.info("已启用 Telegram 通知")

        # 邮件
        if config.email_sender and config.email_password and config.email_receivers:
            receivers = config.get_email_receiver_list()
            if receivers:
                notifiers.append(EmailNotifier(
                    smtp_host=config.email_smtp_host,
                    smtp_port=config.email_smtp_port,
                    sender=config.email_sender,
                    password=config.email_password,
                    receivers=receivers,
                ))
                logger.info(f"已启用邮件通知: {receivers}")

        if not notifiers:
            logger.warning("未配置任何通知渠道")

        return cls(notifiers)

    async def broadcast(self, title: str, content: str) -> dict[str, bool]:
        """并发发送到所有渠道，返回各渠道结果"""
        if not self.notifiers:
            logger.warning("没有可用的通知渠道")
            return {}

        results = {}
        tasks = []

        for notifier in self.notifiers:
            channel_name = notifier.__class__.__name__
            tasks.append(self._send_with_name(channel_name, notifier, title, content))

        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(task_results):
            channel_name = self.notifiers[i].__class__.__name__
            if isinstance(result, Exception):
                results[channel_name] = False
                logger.error(f"{channel_name} 推送异常: {result}")
            else:
                results[channel_name] = result

        return results

    async def _send_with_name(
        self, name: str, notifier: BaseNotifier, title: str, content: str
    ) -> bool:
        """发送单个渠道"""
        try:
            return await notifier.send(title, content)
        except Exception as e:
            logger.error(f"{name} 发送失败: {e}")
            return False
