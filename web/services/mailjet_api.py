import os
import random
import time
from mailjet_rest import Client, CriticalApiError

env = os.environ

# Email configuration
MY_EMAIL: str = env.get("EMAIL_ADDRESS", "")
EMAIL_PASSWORD: str = env.get("EMAIL_PASSWORD", "")
MAILJET_API_KEY: str = env.get("MAILJET_API_KEY", "")
MAILJET_SECRET_KEY: str = env.get("MAILJET_SECRET_KEY", "")

# Retry Configuration
MAX_RETRIES = 2
MAILJET_TIMEOUT = 3
BASE_BACKOFF = 0.5
MAX_BACKOFF = 2.0


def _make_contact_messages(name: str, email: str, reason: str, message: str, send_copy: bool = False) -> dict:
    """
    Create contact data for Mailjet.
    :param name:
    :param email:
    :param reason:
    :param message:
    :param send_copy:
    :return: message_data
    """
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


def _send_to_mailjet(client: Client, data: dict):
    """Send email through Mailjet."""
    return client.send.create(data=data)


def _backoff(attempt: int) -> float:
    """Exponential backoff with a small amount of jitter."""
    delay = min(
        BASE_BACKOFF * (2 ** attempt),
        MAX_BACKOFF,
    )

    delay += random.uniform(0, delay * 0.25)

    print(f"[Mailjet] Retrying in {delay:.2f}s...")
    time.sleep(delay)

    return delay


def send_email(name: str, email: str, reason: str, message: str, send_copy: bool = False) -> str | None:
    """
        Send email through Mailjet.
        Returns: None on success.
        A human-readable error message on failure.
        The function:
            - Uses a short Mailjet HTTP timeout.
            - Retries transient HTTP errors (429 and 5xx).
            - Retries network/timeout errors.
            - Does not retry permanent 4xx errors.
            - Uses exponential backoff with jitter.
    """
    if not MAILJET_API_KEY or not MAILJET_SECRET_KEY:
        return "Mailjet API credentials missing."

    data = _make_contact_messages(
        name.title(),
        email.lower(),
        reason.capitalize(),
        message,
        send_copy
    )

    with Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1', timeout=MAILJET_TIMEOUT) as client:
        # Send to inbox
        for attempt in range(MAX_RETRIES + 1):
            attempt_number = attempt + 1

            print(
                f"[Mailjet] Sending email "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1})..."
            )

            try:
                response = _send_to_mailjet(client, data)
            except TimeoutError:
                print(
                    f"[Mailjet] Request timed out "
                    f"(attempt {attempt_number}/{MAX_RETRIES + 1})."
                )

                if attempt >= MAX_RETRIES:
                    print("[Mailjet] Maximum retries reached.")
                    return (
                        "Mailjet timed out while sending the message. "
                        "Please try again later."
                    )

                _backoff(attempt)
                continue

            except CriticalApiError as e:
                print(
                    f"[Mailjet] Connection/API error "
                    f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
                )

                if attempt >= MAX_RETRIES:
                    print("[Mailjet] Maximum retries reached.")
                    return (
                        "Could not connect to the email service. "
                        "Please try again later."
                    )

                _backoff(attempt)
                continue

            status = response.status_code

            try:
                body = response.json()
            except ValueError:
                body = {}

            print(f"[Mailjet] HTTP {status}")

            if body:
                print(f"[Mailjet] Response: {body}")

            # Success
            if 200 <= status < 300:
                print("[Mailjet] Email accepted successfully.")
                return None

            # Rate limit
            if status == 429:
                print("[Mailjet] Rate limited (429).")

                if attempt >= MAX_RETRIES:
                    print("[Mailjet] Maximum retries reached.")
                    return (
                        "The email service is temporarily rate limited. "
                        "Please try again later."
                    )

                _backoff(attempt)
                continue

            # Server error
            if 500 <= status < 600:
                print(f"[Mailjet] Server error ({status}).")

                if attempt >= MAX_RETRIES:
                    print("[Mailjet] Maximum retries reached.")
                    return (
                        "The email service is temporarily unavailable. "
                        "Please try again later."
                    )

                _backoff(attempt)
                continue

            # Client/request error
            if 400 <= status < 500:
                for msg in body["Messages"]:
                    for error in msg["Errors"]:
                        print(
                            f"[Mailjet] Error: {error["ErrorMessage"]}\n"
                            f"[Mailjet] Error related to: {error["ErrorRelatedTo"]}"
                        )

                print(f"[Mailjet] Request rejected ({status}).")
                return f"Mailjet rejected the email (HTTP {status})."

            # Unexpected status
            print(f"[Mailjet] Unexpected HTTP status: {status}")
            return f"Unexpected Mailjet response (HTTP {status})."

        return "Unable to send email."
