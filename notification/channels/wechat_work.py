"""企业微信 Webhook 通知"""

import logging

import httpx

from notification.base import BaseNotifier

logger = logging.getLogger(__name__)


class WechatWorkNotifier(BaseNotifier):
    """企业微信机器人通知"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, title: str, content: str) -> bool:
        """发送企业微信消息"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json={
                        "msgtype": "markdown",
                        "markdown": {
                            "content": f"## {title}\n\n{content}",
                        },
                    },
                    timeout=30,
                )
                data = response.json()
                if data.get("errcode") == 0:
                    logger.info("企业微信推送成功")
                    return True
                else:
                    logger.error(f"企业微信推送失败: {data}")
                    return False
        except Exception as e:
            logger.error(f"企业微信推送异常: {e}")
            return False
