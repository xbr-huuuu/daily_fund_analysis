"""Telegram Bot 通知"""

import logging

import httpx

from notification.base import BaseNotifier

logger = logging.getLogger(__name__)


class TelegramNotifier(BaseNotifier):
    """Telegram Bot 通知"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_base = f"https://api.telegram.org/bot{bot_token}"

    async def send(self, title: str, content: str) -> bool:
        """发送 Telegram 消息"""
        try:
            text = f"*{title}*\n\n{content}"
            # Telegram 消息长度限制 4096
            if len(text) > 4000:
                text = text[:4000] + "\n\n... (内容已截断)"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                    },
                    timeout=30,
                )
                data = response.json()
                if data.get("ok"):
                    logger.info("Telegram 推送成功")
                    return True
                else:
                    logger.error(f"Telegram 推送失败: {data}")
                    return False
        except Exception as e:
            logger.error(f"Telegram 推送异常: {e}")
            return False
