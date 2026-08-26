import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

from backend.app.core.config import WebSettings


class MailSender(Protocol):
    """定义邀请邮件发送边界，业务逻辑不依赖具体 SMTP 实现。"""

    def send_invitation(self, email: str, role: str, invitation_url: str) -> None:
        """发送一次性邀请链接。"""


class SmtpMailSender:
    """通过标准 SMTP 发送生产邀请邮件。"""

    def __init__(self, settings: WebSettings) -> None:
        self.settings = settings

    def send_invitation(self, email: str, role: str, invitation_url: str) -> None:
        message = EmailMessage()
        message["Subject"] = "积加数据同步邀请"
        message["From"] = self.settings.smtp_from
        message["To"] = email
        message.set_content(
            f"你已被邀请为 {role}。请使用以下一次性链接完成注册：\n{invitation_url}"
        )

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as client:
            if self.settings.smtp_use_tls:
                client.starttls()
            if self.settings.smtp_user:
                client.login(self.settings.smtp_user, self.settings.smtp_password)
            client.send_message(message)


class ConsoleMailSender:
    """只在本地终端输出邀请链接，避免写入应用日志文件。"""

    def send_invitation(self, email: str, role: str, invitation_url: str) -> None:
        print(f"邀请邮箱: {email}")
        print(f"邀请角色: {role}")
        print(f"邀请链接: {invitation_url}")


@dataclass
class FakeMailSender:
    """在自动化测试中捕获邮件，不访问外部服务。"""

    invitations: list[dict[str, str]] = field(default_factory=list)

    def send_invitation(self, email: str, role: str, invitation_url: str) -> None:
        self.invitations.append({"email": email, "role": role, "url": invitation_url})


def create_mail_sender(settings: WebSettings) -> MailSender:
    """根据环境配置创建邮件适配器。"""
    if settings.mail_provider == "smtp":
        return SmtpMailSender(settings)
    if settings.mail_provider == "fake":
        return FakeMailSender()
    return ConsoleMailSender()
