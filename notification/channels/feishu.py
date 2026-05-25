"""飞书 Webhook 通知"""

import logging

import httpx

from notification.base import BaseNotifier

logger = logging.getLogger(__name__)


class FeishuNotifier(BaseNotifier):
    """飞书机器人通知"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, title: str, content: str) -> bool:
        """发送飞书消息"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json={
                        "msg_type": "interactive",
                        "card": {
                            "header": {
                                "title": {
                                    "tag": "plain_text",
                                    "content": title,
                                },
                            },
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": content,
                                },
                            ],
                        },
                    },
                    timeout=30,
                )
                data = response.json()
                if data.get("code") == 0 or data.get("StatusCode") == 0:
                    logger.info("飞书推送成功")
                    return True
                else:
                    logger.error(f"飞书推送失败: {data}")
                    return False
        except Exception as e:
            logger.error(f"飞书推送异常: {e}")
            return False
