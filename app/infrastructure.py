import logging
import smtplib
from email.message import EmailMessage
from io import BytesIO
from typing import List

from imap_tools import AND, MailBox, MailboxLoginError, MailMessage

from utils import parse_error

logger = logging.getLogger("EMAIL")


class EMailService:
    USER = "padronparser@yahoo.com"
    PASSWORD = "oimttdiepntcfkaj"
    IMAP_URL = "imap.mail.yahoo.com"
    SMTP_URL = "smtp.mail.yahoo.com"


class ImapService(EMailService):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.disconnect()

    def connect(self):
        logger.info("Connecting to IMAP")
        try:
            self.connection = MailBox(self.IMAP_URL)
            self.connection.login(self.USER, self.PASSWORD)
            logger.info(self.connection.login_result[1][0].decode("utf-8"))
        except Exception as e:
            raise ConnectionError(parse_error(e))

    def disconnect(self):
        logger.info("Logging out")
        try:
            self.connection.logout()
        except Exception as e:
            raise ConnectionError(parse_error(e))

    def fetch_emails(self, seen: bool = False, mark_seen: bool = True, **kwargs: dict) -> List[MailMessage]:
        logger.info("Fetching emails")
        try:
            msgs = [msg for msg in self.connection.fetch(AND(seen=seen, **kwargs), mark_seen=mark_seen)]
            logger.info(f"Retrieved {len(msgs)} emails")
            return list(msgs)
        except Exception as e:
            raise ConnectionError(parse_error(e))


class SmtpService(EMailService):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.disconnect()

    def connect(self):
        logger.info("Connecting to SMTP")
        try:
            self.connection = smtplib.SMTP_SSL(self.SMTP_URL, 465)
            _, msg = self.connection.login(self.USER, self.PASSWORD)
            logger.info(msg.decode("utf-8"))
        except Exception as e:
            raise ConnectionError(parse_error(e))

    def disconnect(self):
        logger.info("Logging out")
        self.connection.quit()

    def send_email(self, to: str, subject: str, attachments: List[dict] = None):
        msg = EmailMessage()
        msg["Subject"] = f"{subject}_PROCESADO"
        msg["From"] = self.USER
        msg["To"] = to

        try:
            for att in attachments:
                binary_data = att["data"]
                if isinstance(att["data"], BytesIO):
                    att["data"].seek(0)
                    binary_data = att["data"].read()
                msg.add_attachment(binary_data, maintype="application", subtype="xlsx", filename=att["file_name"])
            logger.info(f"Sending email to {to}")
            self.connection.send_message(msg)
        except Exception as e:
            raise ConnectionError(parse_error(e))


imap = ImapService()
smtp = SmtpService()
