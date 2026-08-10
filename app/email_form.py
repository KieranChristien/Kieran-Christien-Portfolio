from email.message import EmailMessage
from dotenv import load_dotenv
import os
import smtplib

load_dotenv()
env = os.environ

EMAIL_ADDRESS: str = env.get("EMAIL_ADDRESS", "")
EMAIL_PASSWORD: str = env.get("EMAIL_PASSWORD", "")
SMTP_ADDRESS: str = env.get("SMTP_ADDRESS", "")
SMTP_PORT: int = int(env.get("SMTP_PORT", "587"))


class EmailForm:
    def __init__(self, name: str, email: str, reason: str, msg: str, send_copy: bool):
        self.name = name.title()
        self.email = email.lower()
        self.reason = reason.title()
        self.message = msg
        self.send_copy = send_copy

    def send(self):
        with smtplib.SMTP(host=SMTP_ADDRESS, port=SMTP_PORT) as connection:
            connection.starttls()
            connection.login(user=EMAIL_ADDRESS, password=EMAIL_PASSWORD)

            msg = EmailMessage()
            msg['Subject'] = f"[{self.reason}] Requested From {self.name} ({self.email})"
            msg['From'] = EMAIL_ADDRESS
            msg['To'] = EMAIL_ADDRESS
            msg.set_content(self.message)

            connection.send_message(msg)

            if self.send_copy:
                msg.replace_header("Subject", f"[{self.reason}] Requested")
                msg.replace_header("To", self.email)

                connection.send_message(msg)
