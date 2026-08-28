from cloudinary import uploader
from flask import current_app

def upload_image_file(file_storage, folder="portfolio/projects", eager=None, eager_async=False, use_filename=True) -> \
        tuple[None, str] | tuple[dict, None]:
    """
    Upload wrapper: returns (response, error_message)\n
    On success: (response_dict, None)\n
    On failure: (None, 'human message')
    """
    if not file_storage:
        return None, "No file provided."

    try:
        file_storage.stream.seek(0)
    except Exception:
        pass

    try:
        kwargs = dict(
            folder=folder,
            resource_type="image",
            use_filename=use_filename,
            unique_filename=True,
            overwrite=False,
        )
        if eager is not None:
            kwargs.update({"eager": eager, "eager_async": eager_async})
        resp = uploader.upload(file_storage, **kwargs)
        return resp, None
    except Exception:
        current_app.logger.exception("Cloudinary upload failed for %s.", getattr(file_storage, "filename", "<unknown>"))
        return None, f"Failed to upload {getattr(file_storage, 'filename', 'file')}."


def delete_image_file(image_id) -> str | None:
    """
    Delete wrapper: returns error_message\n
    On success: None\n
    On failure: 'human message'
    """
    if not image_id:
        return "No id provided."

    try:
        if image_id:
            uploader.destroy(image_id, resource_type="image", invalidate=True)
            return None
    except Exception:
        current_app.logger.exception("Cloudinary deletion failed for %s.", image_id)
        return f"Failed to delete {image_id}."