import random
import time
from flask import current_app
from mailjet_rest import Client, CriticalApiError

# Retry Configuration
MAX_ATTEMPTS = 3
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
    work_email = current_app.config["WORK_EMAIL"]

    msg = {
        "From": {
            "Email": "contact@kieran-christien-dev.com",
            "Name": "Kieran Christien Dev"
        },
        "To": [
            {
                "Email": work_email,
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
            "Email": work_email,
            "Name": "Kieran Christien"
        },
        "Subject": "Contact Form",
        "TextPart": f"Thanks for contacting me, {name}. I received your message and will reply within 2 business days.\n\n"
                    f"Your message:\n{message}"
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


def _backoff(attempt: int) -> None:
    """Exponential backoff with a small amount of jitter."""
    delay = min(
        BASE_BACKOFF * (2 ** attempt),
        MAX_BACKOFF,
    )

    delay += random.uniform(0, delay * 0.25)

    current_app.logger.info("[Mailjet] Retrying in %.2fs...", delay)
    time.sleep(delay)


def _can_retry(attempt: int) -> bool:
    return attempt < MAX_ATTEMPTS - 1


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
    api_key: str | None = current_app.config["MAILJET_API_KEY"]
    secret_key: str | None = current_app.config["MAILJET_SECRET_KEY"]

    if not api_key or not secret_key:
        return "Mailjet API credentials missing."

    data = _make_contact_messages(
        name.title(),
        email.lower(),
        reason.capitalize(),
        message,
        send_copy
    )

    with Client(auth=(api_key, secret_key), version='v3.1', timeout=MAILJET_TIMEOUT) as client:
        # Send to inbox
        for attempt in range(MAX_ATTEMPTS):
            attempt_number = attempt + 1

            current_app.logger.info(
                "[Mailjet] Sending email "
                "(attempt %s/%s)...",
                attempt_number,
                MAX_ATTEMPTS,
            )

            try:
                response = _send_to_mailjet(client, data)
            except TimeoutError:
                current_app.logger.exception(
                    "[Mailjet] Request timed out "
                    "(attempt %s/%s).",
                    attempt_number,
                    MAX_ATTEMPTS,
                )

                if _can_retry(attempt):
                    _backoff(attempt)
                    continue

                current_app.logger.error("[Mailjet] Maximum retries reached.")
                return (
                    "Mailjet timed out while sending the message. "
                    "Please try again later."
                )

            except CriticalApiError as e:
                current_app.logger.exception(
                    "[Mailjet] Connection/API error "
                    "(attempt %s/%s): %s",
                    attempt_number,
                    MAX_ATTEMPTS,
                    e,
                )

                if _can_retry(attempt):
                    _backoff(attempt)
                    continue

                current_app.logger.error("[Mailjet] Maximum retries reached.")
                return (
                    "Could not connect to the email service. "
                    "Please try again later."
                )

            status = response.status_code

            try:
                body = response.json()
            except ValueError:
                body = {}

            current_app.logger.info("[Mailjet] HTTP %s", status)

            # Success
            if 200 <= status < 300:
                current_app.logger.info("[Mailjet] Email accepted successfully.")
                return None

            # Rate limit
            if status == 429:
                current_app.logger.warning("[Mailjet] Rate limited (429).")

                if _can_retry(attempt):
                    _backoff(attempt)
                    continue

                current_app.logger.error("[Mailjet] Maximum retries reached.")
                return (
                    "The email service is temporarily rate limited. "
                    "Please try again later."
                )

            # Server error
            if 500 <= status < 600:
                current_app.logger.warning("[Mailjet] Server error (%s).", status)

                if _can_retry(attempt):
                    _backoff(attempt)
                    continue

                current_app.logger.error("[Mailjet] Maximum retries reached.")
                return (
                    "The email service is temporarily unavailable. "
                    "Please try again later."
                )

            # Client/request error
            if 400 <= status < 500:
                for msg in body.get("Messages", []):
                    for error in msg.get("Errors", []):
                        current_app.logger.error(
                            "[Mailjet] Error: %s\n"
                            "[Mailjet] Error related to: %s",
                            error.get("ErrorMessage", ""),
                            error.get("ErrorRelatedTo", ""),
                        )

                current_app.logger.error("[Mailjet] Request rejected (%s).", status)
                return f"Mailjet rejected the email (HTTP {status})."

            # Unexpected status
            current_app.logger.error("[Mailjet] Unexpected HTTP status: %s", status)
            return f"Unexpected Mailjet response (HTTP {status})."

        return "Unable to send email."
