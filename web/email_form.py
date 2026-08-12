from dotenv import load_dotenv
from mailjet_rest import Client
import os

load_dotenv()
env = os.environ

ATTEMPTS = 2

MY_EMAIL: str = env.get("EMAIL_ADDRESS", "")
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

    def _make_message(self):
        msg = {
            "From": {
                "Email": "contact@kieran-christien-dev.com",
                "Name": "Kieran Christien Dev"
            },
            "To": [
                {
                    "Email": MY_EMAIL,
                    "Name": "Kieran Christien"
                }
            ],
            "ReplyTo": {
                "Email": self.email,
                "Name": self.name
            },
            "Subject": f"[{self.reason}] From {self.name}",
            "TextPart": self.message
        }

        msg_copy = {
            "From": {
                "Email": "contact@kieran-christien-dev.com",
                "Name": "Kieran Christien Dev"
            },
            "To": [
                {
                    "Email": self.email,
                    "Name": self.name
                }
            ],
            "ReplyTo": {
                "Email": MY_EMAIL,
                "Name": "Kieran Christien"
            },
            "Subject": f"Contact Form",
            "TextPart": f"Thanks for contacting me {self.name}. I received your message and will reply within 2 business days.\n\n"
                        f"Your message:\n {self.message}"
        }

        messages = [
            msg
        ]
        if self.send_copy:
            messages.append(msg_copy)

        return {'Messages': messages}

    def send(self):
        if not MAILJET_API_KEY or not MAILJET_SECRET_KEY:
            print("Mailjet API credentials missing", flush=True)
            return

        for attempt in range(1, ATTEMPTS + 1):
            print("EMAIL SEND START", flush=True)
            with Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1') as client:
                # Send to inbox
                try:
                    result = client.send.create(data=self._make_message())
                except Exception as e:
                    print("Mailjet API call failed: ", e, flush=True)
                    return

                if 200 <= result.status_code < 300:
                    print("EMAIL SEND SUCCESS", flush=True)
                    break
                else:
                    print("EMAIL SEND FAIL", flush=True)
