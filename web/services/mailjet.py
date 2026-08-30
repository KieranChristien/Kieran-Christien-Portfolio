import os
from mailjet_rest import Client

env = os.environ

MY_EMAIL: str = env.get("EMAIL_ADDRESS", "")
EMAIL_PASSWORD: str = env.get("EMAIL_PASSWORD", "")
MAILJET_API_KEY: str = env.get("MAILJET_API_KEY", "")
MAILJET_SECRET_KEY: str = env.get("MAILJET_SECRET_KEY", "")


def _make_contact_messages(name: str, email: str, reason: str, message: str, send_copy: bool = False) -> dict:
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
            "Email": email,
            "Name": name
        },
        "Subject": f"[{reason}] {name}",
        "TextPart": message
    }

    msg_copy = {
        "From": {
            "Email": "contact@kieran-christien-dev.com",
            "Name": "Kieran Christien Dev"
        },
        "To": [
            {
                "Email": email,
                "Name": name
            }
        ],
        "ReplyTo": {
            "Email": MY_EMAIL,
            "Name": "Kieran Christien"
        },
        "Subject": f"Contact Form",
        "TextPart": f"Thanks for contacting me, {name}. I received your message and will reply within 2 business days.\n\n"
                    f"Your message:\n {message}"
    }

    messages = [
        msg
    ]
    if send_copy:
        messages.append(msg_copy)

    return {'Messages': messages}


def send_email(name: str, email: str, reason: str, message: str, send_copy: bool = False) -> str | None:
    """
    Send Email wrapper: returns error_message\n
    On success: None\n
    On failure: 'human message'
    """
    if not MAILJET_API_KEY or not MAILJET_SECRET_KEY:
        return "Mailjet API credentials missing."

    with Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1') as client:
        # Send to inbox
        try:
            client.send.create(data=_make_contact_messages(
                name.title(),
                email.lower(),
                reason.capitalize(),
                message,
                send_copy
            ))
        except Exception as e:
            return f"Mailjet API call failed:\n{e}"

        return None
