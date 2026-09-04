import random
import time
from flask import current_app
from typing import Any

from cloudinary import uploader
from cloudinary.exceptions import AlreadyExists, AuthorizationRequired, BadRequest, GeneralError, NotAllowed, \
    NotFound, RateLimited
from werkzeug.datastructures import FileStorage

# Retry Configuration
MAX_ATTEMPTS = 3
CLOUDINARY_TIMEOUT = 3
BASE_BACKOFF = 0.5
MAX_BACKOFF = 2.0


def _backoff(attempt: int) -> None:
    delay = min(
        BASE_BACKOFF * (2 ** attempt),
        MAX_BACKOFF,
    )

    delay += random.uniform(0, delay * 0.25)

    current_app.logger.info("[Cloudinary] Retrying in %.2fs...", delay)
    time.sleep(delay)


def _can_retry(attempt: int) -> bool:
    return attempt < MAX_ATTEMPTS - 1


def _delete_from_cloudinary(image_id: str):
    return uploader.destroy(image_id, resource_type="image", invalidate=True, timeout=CLOUDINARY_TIMEOUT)


def _upload_to_cloudinary(file_storage: FileStorage, **kwargs):
    return uploader.upload(file_storage, timeout=CLOUDINARY_TIMEOUT, **kwargs)


def upload_image_file(file_storage: FileStorage, folder="portfolio/projects", eager=None, eager_async=False,
                      use_filename=True) -> \
        tuple[dict[str, Any], None] | tuple[None, str]:
    """
    Upload wrapper: returns (response, error_message)\n
    On success: (response_dict, None)\n
    On failure: (None, 'human message')
    """
    if file_storage is None:
        return None, "No file provided."

    kwargs = dict(
        folder=folder,
        resource_type="image",
        use_filename=use_filename,
        unique_filename=True,
        overwrite=False,
    )
    if eager is not None:
        kwargs.update({"eager": eager, "eager_async": eager_async})

    for attempt in range(MAX_ATTEMPTS):
        file_storage.stream.seek(0)
        attempt_number = attempt + 1

        current_app.logger.info(
            "[Cloudinary] Uploading %s "
            "(attempt %s/%s)...",
            file_storage.filename,
            attempt_number,
            MAX_ATTEMPTS,
        )

        try:
            response = _upload_to_cloudinary(file_storage, **kwargs)
            current_app.logger.info(
                "[Cloudinary] Image %s uploaded successfully.",
                file_storage.filename,
            )
            return response, None
        except TimeoutError:
            current_app.logger.exception(
                "[Cloudinary] Request timed out "
                "(attempt %s/%s).",
                attempt_number,
                MAX_ATTEMPTS,
            )

            if _can_retry(attempt):
                _backoff(attempt)
                continue

            current_app.logger.error("[Cloudinary] Maximum retries reached.")
            return None, (
                "Cloudinary timed out while uploading the image. "
                "Please try again later."
            )

        except AuthorizationRequired as e:
            current_app.logger.exception(
                "[Cloudinary] Authorization error "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            return None, (
                "Could not authorise connection. "
                "Please authorise connection with Cloudinary."
            )

        except AlreadyExists as e:
            current_app.logger.exception(
                "[Cloudinary] Already exists error "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            return None, "Could not upload image that already exists."

        except BadRequest as e:
            current_app.logger.exception(
                "[Cloudinary] Bad request error "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            return None, "Cloudinary rejected the image."

        except GeneralError as e:
            current_app.logger.exception(
                "[Cloudinary] Connection/API error "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            if _can_retry(attempt):
                _backoff(attempt)
                continue

            current_app.logger.error("[Cloudinary] Maximum retries reached.")
            return None, (
                "Could not connect to the upload service. "
                "Please try again later."
            )

        except NotAllowed as e:
            current_app.logger.exception(
                "[Cloudinary] Request not allowed "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            return None, "Not permitted to upload image."

        except NotFound as e:
            current_app.logger.exception(
                "[Cloudinary] Resource not found "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            return None, "The requested Cloudinary resource was not found."

        except RateLimited as e:
            current_app.logger.exception(
                "[Cloudinary] Rate limited (429) "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            if _can_retry(attempt):
                _backoff(attempt)
                continue

            current_app.logger.error("[Cloudinary] Maximum retries reached.")
            return None, (
                "The upload service is temporarily rate limited. "
                "Please try again later."
            )

    return None, "Unable to upload image."


def delete_image_file(image_id: str | None) -> str | None:
    """
    Delete wrapper: error_message\n
    On success: None\n
    On failure: 'human message'
    """
    if not image_id:
        return "No image ID provided."

    for attempt in range(MAX_ATTEMPTS):
        attempt_number = attempt + 1

        current_app.logger.info(
            "[Cloudinary] Deleting %s "
            "(attempt %s/%s)...",
            image_id,
            attempt_number,
            MAX_ATTEMPTS,
        )

        try:
            _delete_from_cloudinary(image_id)
            current_app.logger.info(
                "[Cloudinary] Deleted %s successfully.",
                image_id,
            )
            return None
        except TimeoutError:
            current_app.logger.exception(
                "[Cloudinary] Request timed out "
                "(attempt %s/%s).",
                attempt_number,
                MAX_ATTEMPTS,
            )

            if _can_retry(attempt):
                _backoff(attempt)
                continue

            current_app.logger.error("[Cloudinary] Maximum retries reached.")
            return (
                "Cloudinary timed out while deleting the image. "
                "Please try again later."
            )

        except AuthorizationRequired as e:
            current_app.logger.exception(
                "[Cloudinary] Authorization error "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            return (
                "Could not authorise connection. "
                "Please authorise connection with Cloudinary."
            )

        except BadRequest as e:
            current_app.logger.exception(
                "[Cloudinary] Bad request error "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            return "Cloudinary rejected the delete request."

        except GeneralError as e:
            current_app.logger.exception(
                "[Cloudinary] Connection/API error "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            if _can_retry(attempt):
                _backoff(attempt)
                continue

            current_app.logger.error("[Cloudinary] Maximum retries reached.")
            return (
                "Could not connect to the delete service. "
                "Please try again later."
            )

        except NotAllowed as e:
            current_app.logger.exception(
                "[Cloudinary] Request not allowed "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            return "Not permitted to delete image."

        except NotFound as e:
            current_app.logger.exception(
                "[Cloudinary] Resource already deleted "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            return None

        except RateLimited as e:
            current_app.logger.exception(
                "[Cloudinary] Rate limited (429) "
                "(attempt %s/%s): %s",
                attempt_number,
                MAX_ATTEMPTS,
                e
            )

            if _can_retry(attempt):
                _backoff(attempt)
                continue

            current_app.logger.error("[Cloudinary] Maximum retries reached.")
            return (
                "The delete service is temporarily rate limited. "
                "Please try again later."
            )

    return "Unable to delete image."
