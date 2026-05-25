"""邮件 SMTP 通知"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from notification.base import BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """邮件通知"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender: str,
        password: str,
        receivers: list[str],
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender
        self.password = password
        self.receivers = receivers

    async def send(self, title: str, content: str) -> bool:
        """发送邮件"""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = title
            msg["From"] = self.sender
            msg["To"] = ", ".join(self.receivers)

            # 纯文本内容
            text_part = MIMEText(content, "plain", "utf-8")
            msg.attach(text_part)

            # HTML 内容
            html_content = content.replace("\n", "<br>")
            html_part = MIMEText(
                f"<html><body><pre>{html_content}</pre></body></html>",
                "html",
                "utf-8",
            )
            msg.attach(html_part)

            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.sender, self.password)
                server.sendmail(self.sender, self.receivers, msg.as_string())

            logger.info(f"邮件推送成功: {self.receivers}")
            return True
        except Exception as e:
            logger.error(f"邮件推送异常: {e}")
            return False
