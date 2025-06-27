import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from utils.templates import TemplatesHandler


class Email:
    VERIFY_LINK = '{BASE_PATH}/api/user/verify?token={TOKEN}'
    VERIFY_TEMPLATE = 'verify-mail'
    RESET_PASSWORD_LINK = '{BASE_PATH}/api/user/reset?token={TOKEN}'
    RESET_PASSWORD_TEMPLATE = 'password-reset-mail'
    def __init__(self,
                 smtp_server: str,
                 port: int,
                 username: str,
                 password: str,
                 from_email: str,
                 template: TemplatesHandler,
                 base_path: str
                 ):
        self._smtp_server = smtp_server
        self._port = port
        self._username = username
        self._password = password
        self.from_email = from_email
        self._template = template
        self._base_path = base_path

    def _get_message(self, subject: str, to: str):
        """
        Returns base message
        :param subject: Email subject
        :param to: Email receiver
        """
        msg = MIMEMultipart('alternative')
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to
        return msg
    def _send(self, msg: MIMEMultipart):
        """
        Logins to SMTP server and sends email
        :param msg: Message content
        """
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self._smtp_server, self._port, context=context) as server:
            server.login(self._username, self._password)
            server.send_message(msg)
    def send(self, subject: str, to_email: str, html_content: str):
        """
        Sends email
        :param subject: Email subject
        :param to_email: Email receiver
        :param html_content: HTML content for body
        :return:
        """
        msg = self._get_message(subject, to_email)

        html = MIMEText(html_content, 'html')
        msg.attach(html)

        self._send(msg)

    def send_verification_email(self, to_email: str, token: str):
        link = self.VERIFY_LINK.format(BASE_PATH=self._base_path, TOKEN=token)
        content = self._template.render(self.VERIFY_TEMPLATE, link=link)
        self.send('Verify your email', to_email, content)

    def send_password_reset(self, to_email: str, token: str):
        link = self.RESET_PASSWORD_LINK.format(BASE_PATH=self._base_path, TOKEN=token)
        content = self._template.render(self.RESET_PASSWORD_TEMPLATE, link=link)
        self.send('Reset your password', to_email, content)
