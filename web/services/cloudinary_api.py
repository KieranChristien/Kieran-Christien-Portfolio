import random
import time
from cloudinary import uploader
from cloudinary.exceptions import AlreadyExists, AuthorizationRequired, BadRequest, GeneralError, NotAllowed, \
    NotFound, RateLimited
from werkzeug.datastructures import FileStorage

# Retry Configuration
MAX_RETRIES = 2
CLOUDINARY_TIMEOUT = 3
BASE_BACKOFF = 0.5
MAX_BACKOFF = 2.0


def _backoff(attempt: int) -> float:
    """Exponential backoff with a small amount of jitter."""
    delay = min(
        BASE_BACKOFF * (2 ** attempt),
        MAX_BACKOFF,
    )

    delay += random.uniform(0, delay * 0.25)

    print(f"[Cloudinary] Retrying in {delay:.2f}s...")
    time.sleep(delay)

    return delay


def _delete_from_cloudinary(image_id: str):
    return uploader.destroy(image_id, resource_type="image", invalidate=True, timeout=CLOUDINARY_TIMEOUT)


def _upload_to_cloudinary(file_storage: FileStorage, **kwargs):
    return uploader.upload(file_storage, timeout=CLOUDINARY_TIMEOUT, **kwargs)


def upload_image_file(file_storage: FileStorage, folder="portfolio/projects", eager=None, eager_async=False,
                      use_filename=True) -> \
        tuple[dict, None] | tuple[None, str]:
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

    for attempt in range(MAX_RETRIES + 1):
        file_storage.stream.seek(0)
        attempt_number = attempt + 1

        print(
            f"[Cloudinary] Uploading image "
            f"(attempt {attempt_number}/{MAX_RETRIES + 1})..."
        )

        try:
            return _upload_to_cloudinary(file_storage, **kwargs), None
        except TimeoutError:
            print(
                f"[Cloudinary] Request timed out "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1})."
            )

            if attempt >= MAX_RETRIES:
                print("[Cloudinary] Maximum retries reached.")
                return None, (
                    "Cloudinary timed out while uploading the image. "
                    "Please try again later."
                )

            _backoff(attempt)
            continue

        except AuthorizationRequired as e:
            print(
                f"[Cloudinary] Authorization error "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            return None, (
                "Could not authorise connection. "
                "Please authorise connection with Cloudinary."
            )

        except AlreadyExists as e:
            print(
                f"[Cloudinary] Already exists error "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            return None, "Could not upload image that already exists."

        except BadRequest as e:
            print(
                f"[Cloudinary] Bad request error "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            return None, "Cloudinary rejected the image."

        except GeneralError as e:
            print(
                f"[Cloudinary] Connection/API error "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            if attempt >= MAX_RETRIES:
                print("[Cloudinary] Maximum retries reached.")
                return None, (
                    "Could not connect to the upload service. "
                    "Please try again later."
                )

            _backoff(attempt)
            continue

        except NotAllowed as e:
            print(
                f"[Cloudinary] Request not allowed "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            return None, "Not permitted to upload image."

        except NotFound as e:
            print(
                f"[Cloudinary] Resource not found "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            return None, "The requested Cloudinary resource was not found."

        except RateLimited as e:
            print(
                f"[Cloudinary] Rate limited (429) "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            if attempt >= MAX_RETRIES:
                print("[Cloudinary] Maximum retries reached.")
                return None, (
                    "The upload service is temporarily rate limited. "
                    "Please try again later."
                )

            _backoff(attempt)
            continue
        finally:
            print("[Cloudinary] Image uploaded successfully.")

    return None, "Unable to upload image."


def delete_image_file(image_id) -> str | None:
    """
    Delete wrapper: error_message\n
    On success: None\n
    On failure: 'human message'
    """
    if not image_id:
        return "No image ID provided."

    for attempt in range(MAX_RETRIES + 1):
        attempt_number = attempt + 1

        print(
            f"[Cloudinary] Deleting image "
            f"(attempt {attempt_number}/{MAX_RETRIES + 1})..."
        )

        try:
            _delete_from_cloudinary(image_id)
            return None
        except TimeoutError:
            print(
                f"[Cloudinary] Request timed out "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1})."
            )

            if attempt >= MAX_RETRIES:
                print("[Cloudinary] Maximum retries reached.")
                return (
                    "Cloudinary timed out while deleting the image. "
                    "Please try again later."
                )

            _backoff(attempt)
            continue

        except AuthorizationRequired as e:
            print(
                f"[Cloudinary] Authorization error "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            return (
                "Could not authorise connection. "
                "Please authorise connection with Cloudinary."
            )

        except BadRequest as e:
            print(
                f"[Cloudinary] Bad request error "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            return "Cloudinary rejected the delete request."

        except GeneralError as e:
            print(
                f"[Cloudinary] Connection/API error "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            if attempt >= MAX_RETRIES:
                print("[Cloudinary] Maximum retries reached.")
                return (
                    "Could not connect to the delete service. "
                    "Please try again later."
                )

            _backoff(attempt)
            continue

        except NotAllowed as e:
            print(
                f"[Cloudinary] Request not allowed "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            return "Not permitted to delete image."

        except NotFound as e:
            print(
                f"[Cloudinary] Resource not found "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            return "The requested Cloudinary resource was not found."

        except RateLimited as e:
            print(
                f"[Cloudinary] Rate limited (429) "
                f"(attempt {attempt_number}/{MAX_RETRIES + 1}): {e}"
            )

            if attempt >= MAX_RETRIES:
                print("[Cloudinary] Maximum retries reached.")
                return (
                    "The delete service is temporarily rate limited. "
                    "Please try again later."
                )

            _backoff(attempt)
            continue
        finally:
            print("[Cloudinary] Image deleted successfully.")

    return "Unable to delete image."
