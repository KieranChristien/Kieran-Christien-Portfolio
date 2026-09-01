from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, fresh_login_required

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

def _editor_context(project, form, is_edit=True):
    return {
        "project_id": getattr(project, "id", None),
        "project_image": getattr(project, "image", None),
        "project_image_width": getattr(project, "image_width", None),
        "project_image_height": getattr(project, "image_height", None),
        "project_thumbnail_1x": getattr(project, "thumbnail_1x", None),
        "project_thumbnail_2x": getattr(project, "thumbnail_2x", None),
        "form": form,
        "is_edit": is_edit,
    }


def render_editor(project, form, status_code=200):
    ctx = _editor_context(project, form, is_edit=True)
    return render_template("project_editor.html", **ctx), status_code


def flash_and_render_editor(message, category, project, form, status_code=200):
    flash(message, category)
    return render_editor(project, form, status_code)

@projects.route('/add-project', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
@fresh_login_required
def add():
    form = AddProjectForm()
    if form.validate_on_submit():
        image_file = form.image.data
        thumbnail_file = form.thumbnail.data

        # Validate image files
        if not (image_file or thumbnail_file):
            flash("Please select an image and thumbnail file.", "error")
            return render_template('project_editor.html', form=form)

        # Upload project image
        image_response, err = upload_image_file(form.image.data)
        if err:
            current_app.logger.error(err)
            flash(err, "error")
            return render_template('project_editor.html', form=form)

        image_id = image_response.get("public_id", "")
        image_url = image_response.get("secure_url", "")
        width = image_response.get("width", "")
        height = image_response.get("height", "")

        # Upload project thumbnail
        thumbnail_response, err = upload_image_file(
            form.thumbnail.data,
            eager=THUMBNAIL_TRANSFORMS,
            eager_async=True,
            use_filename=True
        )
        if err:
            # If thumbnail upload fails, remove the previously uploaded project image
            delete_err = delete_image_file(image_id)
            if delete_err:
                current_app.logger.error(delete_err)
                flash(delete_err, "error")
                return render_template('project_editor.html', form=form)

            current_app.logger.error(err)
            flash(err, "error")
            return render_template('project_editor.html', form=form)

        thumbnail_id = thumbnail_response.get("public_id")
        eager_response = thumbnail_response.get("eager")
        thumb_600 = eager_response[0].get("secure_url") if len(eager_response) > 0 else None
        thumb_1200 = eager_response[1].get("secure_url") if len(eager_response) > 1 else None

        project = Project(
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

        db.session.add(project)
        db.session.commit()

        current_app.logger.info("Admin %s created project %s", current_user.name, project.title)
        return redirect(url_for('main.home'), 303)

    return render_template('project_editor.html', form=form)


@projects.route('/edit-project/<int:project_id>', methods=['GET', 'POST'])
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
        changed = any(
            getattr(project, f) != getattr(form, f).data for f in fields) or form.image.data or form.thumbnail.data

        if not changed:
            return flash_and_render_editor("No changes made.", "error", project, form)

        # Handle image change
        if form.image.data:
            image_response, err = upload_image_file(form.image.data)
            if err:
                current_app.logger.error(err)
                return flash_and_render_editor(err, "error", project, form)

            image_id = image_response.get("public_id", "")
            image_url = image_response.get("secure_url", "")
            width = image_response.get("width", "")
            height = image_response.get("height", "")

            if image_url and image_id and width and height:
                # Clean up old project image
                err = delete_image_file(project.image_id)
                if err:
                    current_app.logger.error(err)
                    return flash_and_render_editor(err, "error", project, form)

                project.image = image_url
                project.image_id = image_id
                project.width = width
                project.height = height

        # Handle thumbnail change
        if form.thumbnail.data:
            thumbnail_response, err = upload_image_file(
                form.thumbnail.data,
                eager=THUMBNAIL_TRANSFORMS,
                eager_async=True,
                use_filename=True
            )
            if err:
                current_app.logger.error(err)
                return flash_and_render_editor(err, "error", project, form)

            thumbnail_id = thumbnail_response.get("public_id", "")
            eager_response = thumbnail_response.get("eager", [])
            thumb_600 = eager_response[0].get("secure_url") if len(eager_response) > 0 else ""
            thumb_1200 = eager_response[1].get("secure_url") if len(eager_response) > 1 else ""

            if thumb_600 and thumb_1200 and thumbnail_id:
                # Clean up old project thumbnail
                err = delete_image_file(project.thumbnail_id)
                if err:
                    current_app.logger.error(err)
                    return flash_and_render_editor(err, "error", project, form)

                project.thumbnail_1x = thumb_600
                project.thumbnail_2x = thumb_1200
                project.thumbnail_id = thumbnail_id

        project.title = form.title.data
        project.category = form.category.data
        project.caption = form.caption.data
        project.thumbnail_alt = form.thumbnail_alt.data
        project.url_name = form.url_name.data
        project.url = form.url.data

        db.session.commit()
        current_app.logger.info("Admin %s edited project %s", current_user.name, project.title)
        return redirect(url_for('main.home'), 303)

    return render_editor(project, form)


@projects.route('/delete-project/<int:project_id>', methods=["POST"])
@limiter.limit("10 per minute")
@fresh_login_required
def delete(project_id):
    project = db.get_or_404(Project, project_id)

    # Clean up image
    err = delete_image_file(project.image_id)
    if err:
        current_app.logger.error(err)
        flash(err, "error")
        return redirect(url_for('projects.edit', project_id=project_id), 303)

    # Clean up thumbnail
    err = delete_image_file(project.thumbnail_id)
    if err:
        current_app.logger.error(err)
        flash(err, "error")
        return redirect(url_for('projects.edit', project_id=project_id), 303)

    # Commit to deletion
    db.session.delete(project)
    db.session.commit()

    current_app.logger.info("Admin %s deleted project %s", current_user.name, project.title)
    return redirect(url_for('main.home'))