from dotenv import load_dotenv
from mailjet_rest import Client
import os

load_dotenv()
env = os.environ

ATTEMPTS = 2

EMAIL_ADDRESS: str = env.get("EMAIL_ADDRESS", "")
EMAIL_PASSWORD: str = env.get("EMAIL_PASSWORD", "")
MAILJET_API_KEY: str = env.get("MAILJET_API_KEY", "")
MAILJET_SECRET_KEY: str = env.get("MAILJET_SECRET_KEY", "")


class EmailForm:
    def __init__(self, name: str, email: str, reason: str, msg: str, send_copy: bool):
        self.name = name.title()
        self.email = email.lower()
        self.reason = reason.title()
        self.message = msg
        self.send_copy = send_copy

    def _make_message(self, to_addr, subject):
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": EMAIL_ADDRESS,
                        "Name": "Me"
                    },
                    "To": [
                        {
                            "Email": to_addr,
                            "Name": "You"
                        }
                    ],
                    "Subject": subject,
                    "TextPart": self.message,
                    "HTMLPart": self.message
                }
            ]
        }

        return data

    def send(self):
        if not MAILJET_API_KEY or not MAILJET_SECRET_KEY:
            print("Mailjet API credentials missing", flush=True)
            return

        for attempt in range(1, ATTEMPTS + 1):
            print("EMAIL SEND START", flush=True)
            with Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1') as client:
                # Send to inbox
                subject = f"[{self.reason}] Requested From {self.name} ({self.email})"
                msg = self._make_message(to_addr=EMAIL_ADDRESS, subject=subject)

                result = client.send.create(data=msg)

                # Send copy if requested
                if self.send_copy:
                    copy_subject = f"[{self.reason}] Requested"
                    copy_msg = self._make_message(to_addr=self.email, subject=copy_subject)

                    client.send.create(data=copy_msg)

                if result.status_code == 200:
                    print("EMAIL SEND SUCCESS", flush=True)
                    break
