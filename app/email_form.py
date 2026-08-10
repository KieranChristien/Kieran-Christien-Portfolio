from email.message import EmailMessage
from dotenv import load_dotenv
import os, smtplib, ssl, time, traceback

load_dotenv()
env = os.environ

ATTEMPTS = 2

EMAIL_ADDRESS: str = env.get("EMAIL_ADDRESS", "")
EMAIL_PASSWORD: str = env.get("EMAIL_PASSWORD", "")
SMTP_ADDRESS: str = env.get("SMTP_ADDRESS", "")
SMTP_PORT: int = int(env.get("SMTP_PORT", "587")) # 587 for STARTTLS


class EmailForm:
    def __init__(self, name: str, email: str, reason: str, msg: str, send_copy: bool):
        self.name = name.title()
        self.email = email.lower()
        self.reason = reason.title()
        self.message = msg
        self.send_copy = send_copy

    def _make_message(self, to_addr, subject):
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_addr
        msg.set_content(self.message)
        return msg

    def send(self):
        ctx = ssl.create_default_context()

        for attempt in range(1, ATTEMPTS + 1):
            try:
                with smtplib.SMTP(host=SMTP_ADDRESS, port=SMTP_PORT, timeout=30) as conn:
                    conn.ehlo()
                    # STARTTLS on port 587
                    conn.starttls(context=ctx)
                    conn.ehlo()
                    conn.login(user=EMAIL_ADDRESS, password=EMAIL_PASSWORD)

                    # Send to inbox
                    subject = f"[{self.reason}] Requested From {self.name} ({self.email})"
                    msg = self._make_message(to_addr=EMAIL_ADDRESS, subject=subject)
                    conn.send_message(msg)

                    # Send copy if requested
                    if self.send_copy:
                        copy_subject = f"[{self.reason}] Requested"
                        copy_msg = self._make_message(to_addr=self.email, subject=copy_subject)

                        conn.send_message(copy_msg)

                break

            except Exception as e:
                print(f"Email send attempt {attempt} failed: {e}")
                traceback.print_exc()
                if attempt < attempts:
                    time.sleep(1 + attempt)  # small backoff
                else:
                    print("All email send attempts failed.")
