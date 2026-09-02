from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, fresh_login_required
from sqlalchemy.exc import IntegrityError

from web.services.cloudinary_api import upload_image_file, delete_image_file
from web.extensions import db, limiter
from web.forms import AddProjectForm, EditProjectForm
from web.models import Project

THUMBNAIL_TRANSFORMS = [
    {
        "width": 600,
        "height": 600,
        "crop": "fit",
        "angle": "exif",
        "fetch_format": "auto",
        "quality": "auto"
    },
    {
        "width": 1200,
        "height": 1200,
        "crop": "fit",
        "angle": "exif",
        "fetch_format": "auto",
        "quality": "auto"
    }
]

projects = Blueprint('projects', __name__)


def _cleanup_assets(*public_ids: str | None) -> None:
    for public_id in public_ids:
        if not public_id:
            continue

        err = delete_image_file(public_id)
        if err:
            current_app.logger.error(
                "Failed to delete Cloudinary asset %s: %s",
                public_id,
                err,
            )


def _editor_context(form, project: Project | None, is_edit=True) -> dict:
    return {
        "form": form,
        "project": project,
        "is_edit": is_edit,
    }


def render_editor(form, project: Project | None = None, is_edit=False, status_code=200) -> tuple[str, int]:
    ctx = _editor_context(form=form, project=project, is_edit=is_edit)
    return render_template("project_editor.html", **ctx), status_code


def flash_and_render_editor(message, category, form, project: Project | None = None, is_edit=False, status_code=200) -> \
        tuple[str, int]:
    flash(message, category)
    return render_editor(form=form, project=project, is_edit=is_edit, status_code=status_code)


@projects.route('/project/add', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
@fresh_login_required
def add():
    form = AddProjectForm()
    if form.validate_on_submit():
        image_file = form.image.data
        thumbnail_file = form.thumbnail.data

        # Validate image files
        if not all((image_file, thumbnail_file)):
            return flash_and_render_editor(
                "Please select an image and thumbnail file.",
                "error",
                form
            )

        # Upload project image
        image_response, err = upload_image_file(form.image.data)
        if err:
            current_app.logger.error(err)
            return flash_and_render_editor(err, "error", form)

        image_id: str = image_response.get("public_id", "")
        image_url: str = image_response.get("secure_url", "")
        width: int = image_response.get("width", -1)
        height: int = image_response.get("height", -1)

        if not all((image_url, image_id)) or width < 0 or height < 0:
            current_app.logger.error("Cloudinary returned incomplete image data.")

            _cleanup_assets(image_id)

            return flash_and_render_editor(
                "Unable to process uploaded image. Please try again.",
                "error",
                form,
            )

        # Upload project thumbnail
        thumbnail_response, err = upload_image_file(
            form.thumbnail.data,
            eager=THUMBNAIL_TRANSFORMS,
            use_filename=True
        )
        if err:
            # If thumbnail upload fails, remove the previously uploaded project image
            _cleanup_assets(image_id)

            current_app.logger.error(err)
            return flash_and_render_editor(err, "error", form)

        thumbnail_id: str = thumbnail_response.get("public_id", "")
        eager_response = thumbnail_response.get("eager", [])
        thumb_600: str = eager_response[0].get("secure_url", "") if len(eager_response) > 0 else ""
        thumb_1200: str = eager_response[1].get("secure_url", "") if len(eager_response) > 1 else ""
        if not all((thumbnail_id, thumb_600, thumb_1200)):
            current_app.logger.error("Cloudinary returned incomplete thumbnail data.")

            _cleanup_assets(image_id, thumbnail_id)

            return flash_and_render_editor(
                "Unable to process uploaded thumbnail. Please try again.",
                "error",
                form,
            )

        new_project = Project(
            title=form.title.data,
            category=form.category.data,
            caption=form.caption.data,
            image=image_url,
            image_id=image_id,
            image_width=width,
            image_height=height,
            thumbnail_1x=thumb_600,
            thumbnail_2x=thumb_1200,
            thumbnail_alt=form.thumbnail_alt.data,
            thumbnail_id=thumbnail_id,
            url_name=form.url_name.data,
            url=form.url.data,
        )

        db.session.add(new_project)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

            _cleanup_assets(image_id, thumbnail_id)

            return flash_and_render_editor(
                "Unable to add project. Please try again.",
                "error",
                form,
                new_project,
                status_code=409
            )

        current_app.logger.info("Admin %s created project %s", current_user.name, new_project.title)
        return redirect(url_for('main.home'), 303)

    return render_editor(form)


@projects.route('/project/edit/<int:project_id>', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
@fresh_login_required
def edit(project_id):
    project = db.get_or_404(Project, project_id)
    form = EditProjectForm(
        title=project.title,
        category=project.category,
        caption=project.caption,
        thumbnail_alt=project.thumbnail_alt,
        url_name=project.url_name,
        url=project.url,
    )

    if form.validate_on_submit():
        # Check if anything was changed
        fields = ["title", "category", "caption", "thumbnail_alt", "url_name", "url"]
        has_changed = (
                any(
                    getattr(project, f) != getattr(form, f).data for f in fields
                )
                or bool(form.image.data)
                or bool(form.thumbnail.data)
        )

        if not has_changed:
            return flash_and_render_editor("No changes made.", "error", form, project, True)

        # Handle image change
        image_id: str | None = None
        old_image_id: str | None = None
        if form.image.data:
            image_response, err = upload_image_file(form.image.data)
            if err:
                current_app.logger.error(err)
                return flash_and_render_editor(err, "error", form, project, True)

            image_id: str = image_response.get("public_id", "")
            image_url: str = image_response.get("secure_url", "")
            width: int = image_response.get("width", -1)
            height: int = image_response.get("height", -1)

            if not all((image_url, image_id)) or width < 0 or height < 0:
                current_app.logger.error(
                    "Cloudinary returned incomplete image data for project %s.",
                    project_id,
                )

                _cleanup_assets(image_id)

                return flash_and_render_editor(
                    "Unable to process uploaded image. Please try again.",
                    "error",
                    form,
                    project,
                    True
                )

            old_image_id = project.image_id
            project.image = image_url
            project.image_id = image_id
            project.image_width = width
            project.image_height = height

        # Handle thumbnail change
        thumbnail_id: str | None = None
        old_thumbnail_id: str | None = None
        if form.thumbnail.data:
            thumbnail_response, err = upload_image_file(
                form.thumbnail.data,
                eager=THUMBNAIL_TRANSFORMS,
                use_filename=True
            )
            if err:
                _cleanup_assets(image_id)

                current_app.logger.error(err)
                return flash_and_render_editor(err, "error", form, project, True)

            thumbnail_id: str = thumbnail_response.get("public_id", "")
            eager_response = thumbnail_response.get("eager", [])
            thumb_600: str = eager_response[0].get("secure_url", "") if len(eager_response) > 0 else ""
            thumb_1200: str = eager_response[1].get("secure_url", "") if len(eager_response) > 1 else ""

            if not all((thumb_600, thumb_1200, thumbnail_id)):
                current_app.logger.error(
                    "Cloudinary returned incomplete thumbnail data for project %s.",
                    project_id,
                )

                _cleanup_assets(image_id, thumbnail_id)

                return flash_and_render_editor(
                    "Unable to process uploaded thumbnail. Please try again.",
                    "error",
                    form,
                    project,
                    True
                )

            old_thumbnail_id = project.thumbnail_id
            project.thumbnail_1x = thumb_600
            project.thumbnail_2x = thumb_1200
            project.thumbnail_id = thumbnail_id

        project.title = form.title.data
        project.category = form.category.data
        project.caption = form.caption.data
        project.thumbnail_alt = form.thumbnail_alt.data
        project.url_name = form.url_name.data
        project.url = form.url.data

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

            # Clean up new orphaned assets
            _cleanup_assets(image_id, thumbnail_id)

            current_app.logger.exception("Failed to edit project %s.", project_id)
            return flash_and_render_editor(
                "Unable to save changes. Please try again.",
                "error",
                form,
                project,
                True,
                409,
            )

        # Clean up old orphaned assets
        _cleanup_assets(old_image_id, old_thumbnail_id)

        current_app.logger.info("Admin %s edited project %s", current_user.name, project.title)
        return redirect(url_for('main.home'), 303)

    return render_editor(form, project, True)


@projects.route('/project/delete/<int:project_id>', methods=["POST"])
@limiter.limit("10 per minute")
@fresh_login_required
def delete(project_id):
    project = db.get_or_404(Project, project_id)
    title = project.title
    image_id = project.image_id
    thumbnail_id = project.thumbnail_id

    # Commit to deletion
    db.session.delete(project)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

        current_app.logger.exception("Failed to delete project %s.", project_id)
        return redirect(url_for('projects.edit', project_id=project_id), 409)

    _cleanup_assets(image_id, thumbnail_id)

    current_app.logger.info("Admin %s deleted project %s", current_user.name, title)
    return redirect(url_for('main.home'))
