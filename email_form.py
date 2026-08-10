from email.message import EmailMessage
import smtplib
import os
from dotenv import load_dotenv

load_dotenv()
env = os.environ

SMTP_ADDRESS: str = env.get("SMTP_ADDRESS", "")
SMTP_PORT: int = int(env.get("SMTP_PORT") or 0)
EMAIL_ADDRESS: str = env.get("EMAIL_ADDRESS", "")
EMAIL_PASSWORD: str = env.get("EMAIL_PASSWORD", "")

class EmailForm:
    def __init__(self, name: str, email: str, reason: str, msg: str, send_copy: bool):
        self.name = name.title()
        self.email = email.lower()
        self.reason = reason.title()
        self.message = msg
        self.send_copy = send_copy

    def send(self):
        print(f"Sending email from {self.email}...")

        if not SMTP_ADDRESS:
            raise EnvironmentError("SMTP_ADDRESS is not set")
        if not SMTP_PORT:
            raise EnvironmentError("SMTP_PORT is not set")
        if not EMAIL_ADDRESS:
            raise EnvironmentError("EMAIL_ADDRESS is not set")
        if not EMAIL_PASSWORD:
            raise EnvironmentError("EMAIL_PASSWORD is not set")

        with smtplib.SMTP(host=SMTP_ADDRESS, port=SMTP_PORT) as connection:
            connection.starttls()
            connection.login(user=EMAIL_ADDRESS, password=EMAIL_PASSWORD)

            msg = EmailMessage()
            msg['Subject'] = f"[{self.reason}] Request From {self.name}"
            msg['From'] = EMAIL_ADDRESS
            msg['To'] = EMAIL_ADDRESS
            msg.set_content(
                f"{self.message}"
            )

            connection.send_message(msg)

            if self.send_copy:
                msg.replace_header('Subject', f"[{self.reason}] Request To Kieran Christien")
                msg.replace_header('To', self.email)
                connection.send_message(msg)

        print(f"Sent email from {self.email}!")
