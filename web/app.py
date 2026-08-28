from dotenv import load_dotenv
from cloudinary.uploader import upload
from flask import Flask, current_app, flash, redirect, render_template, request, url_for
from flask_bootstrap import Bootstrap
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import UserMixin, LoginManager, current_user, login_user, login_required, logout_user, \
    fresh_login_required
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String
from urllib.parse import urljoin, urlparse
from web.email_form import EmailForm
from web.forms import AddProjectForm, ContactForm, EditProjectForm, LoginForm, RegisterForm
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
import cloudinary
import os

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

load_dotenv()
env = os.environ

OWNER_EMAIL = env.get("OWNER_EMAIL")
OWNER_PASSWORD = env.get("OWNER_PASSWORD")
OWNER_NAME = env.get("OWNER_NAME", "Admin")

app = Flask(__name__)
app.config['SECRET_KEY'] = env.get('SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
Bootstrap(app)

# Configure Cloudinary
cloudinary.config(
    cloud_name=env.get("CLOUDINARY_NAME"),
    api_key=env.get("CLOUDINARY_KEY"),
    api_secret=env.get("CLOUDINARY_SECRET"),
    secure=True,
)

# Configure Flask-Limiter
app.config['RATELIMIT_STORAGE_URI'] = env.get("STORAGE_URI", "memory://")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
)
limiter.init_app(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."


# CREATE DATABASE
class Base(DeclarativeBase):
    pass

DB_URI = env.get('DB_URI')

if not DB_URI:
    raise RuntimeError("DATABASE_URI is not configured")
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI

db = SQLAlchemy(model_class=Base)
db.init_app(app)


# Create an Admin table for all registered administrators
class Admin(UserMixin, db.Model):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password: Mapped[str] = mapped_column(String(256))
    name: Mapped[str] = mapped_column(String(100))


# Create a Project table for recent projects
class Project(db.Model):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(15))
    caption: Mapped[str] = mapped_column(String(250))
    image: Mapped[str] = mapped_column(String(2048))
    image_id: Mapped[str] = mapped_column(String(2048))
    image_width: Mapped[int] = mapped_column(Integer)
    image_height: Mapped[int] = mapped_column(Integer)
    thumbnail_1x: Mapped[str] = mapped_column(String(2048))
    thumbnail_2x: Mapped[str] = mapped_column(String(2048))
    thumbnail_alt: Mapped[str] = mapped_column(String(100))
    thumbnail_id: Mapped[str] = mapped_column(String(2048))
    url_name: Mapped[str] = mapped_column(String(20))
    url: Mapped[str] = mapped_column(String(2048))


with app.app_context():
    db.create_all()

    if OWNER_EMAIL and OWNER_PASSWORD:
        existing = db.session.execute(db.select(Admin).filter_by(email=OWNER_EMAIL)).scalar_one_or_none()
        if not existing:
            hashed = generate_password_hash(OWNER_PASSWORD, method='pbkdf2:sha256', salt_length=16)
            admin = Admin(
                email=OWNER_EMAIL,
                password=hashed,
                name=OWNER_NAME
            )
            db.session.add(admin)
            db.session.commit()


def owner_required(func):
    """
    Requires the owner to be logged in.

    :param func: The view function to decorate.
    :type func: function
    """

    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.id == 1:
            return current_app.login_manager.unauthorized()

        return func(*args, **kwargs)

    return decorated_view


@login_manager.user_loader
def load_user(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(Admin, uid)


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    flash("Uploaded file is too large. Maximum file size is 16MB.", "error")
    return redirect(request.url)


def is_safe_url(target: str) -> bool:
    """
    Check if target url is local.
    :param target:
    :return:
    """
    host_url = urlparse(request.host_url)
    target_url = urlparse(urljoin(request.host_url, target))

    return target_url.scheme in ("http", "https") and host_url.netloc == target_url.netloc


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
        resp = cloudinary.uploader.upload(file_storage, **kwargs)
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
            cloudinary.uploader.destroy(image_id, resource_type="image", invalidate=True)
            return None
    except Exception:
        current_app.logger.exception("Cloudinary deletion failed for %s.", image_id)
        return f"Failed to delete {image_id}."


# Register new admins into the Admin database
@app.route('/admin-register', methods=["GET", "POST"])
@limiter.limit("10 per minute")
@fresh_login_required
@owner_required
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Check if admin email is already present in the database.
        result = db.session.execute(db.select(Admin).where(Admin.email == form.email.data))
        user = result.scalar()
        if user:
            # Admin already exists
            current_app.logger.info(f"Sign up attempt for existing email {form.email.data}. Redirecting to login page.")
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'), 303)

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=16
        )
        new_admin = Admin(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_admin)
        db.session.commit()

        # This line will authenticate the admin with Flask-Login
        login_user(new_admin)

        current_app.logger.info(f"Admin {new_admin.name} signed up.")
        return redirect(url_for("home"), 303)
    return render_template("register.html", form=form, current_user=current_user)


# Login admin
@app.route('/admin-login', methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        password = form.password.data
        result = db.session.execute(db.select(Admin).where(Admin.email == form.email.data))
        user = result.scalar()

        # Email doesn't exist
        if not user:
            current_app.logger.info(f"Login attempt for unknown email: {form.email.data}.")
            flash("That email does not exist, please try again.")
            return render_template("login.html", form=form, current_user=current_user)

        # Password incorrect
        elif not check_password_hash(user.password, password):
            current_app.logger.info(f"Login attempt failed for {form.email.data}.")
            flash('Password incorrect, please try again.')
            return render_template("login.html", form=form, current_user=current_user)
        else:
            login_user(user)

            # Get the page the user was trying to access
            next_page = request.args.get('next', '')

            if not next_page or not is_safe_url(next_page):
                next_page = url_for('home')

            current_app.logger.info(f"Admin {user.name} logged in.")
            return redirect(next_page, 303)

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/admin-logout', methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def logout():
    current_app.logger.info(f"Admin {current_user.name} logged out.")
    logout_user()
    return redirect(url_for('home'), 303)


@app.route('/add-project', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
@fresh_login_required
def add_project():
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
                flash(delete_err, "error")
                return render_template('project_editor.html', form=form)

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
        return redirect(url_for('home'), 303)

    return render_template('project_editor.html', form=form)


@app.route('/edit-project/<int:project_id>', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
@fresh_login_required
def edit_project(project_id):
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
                return flash_and_render_editor(err, "error", project, form)

            image_id = image_response.get("public_id", "")
            image_url = image_response.get("secure_url", "")
            width = image_response.get("width", "")
            height = image_response.get("height", "")

            if image_url and image_id and width and height:
                # Clean up old project image
                err = delete_image_file(project.image_id)
                if err:
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
                return flash_and_render_editor(err, "error", project, form)

            thumbnail_id = thumbnail_response.get("public_id", "")
            eager_response = thumbnail_response.get("eager", [])
            thumb_600 = eager_response[0].get("secure_url") if len(eager_response) > 0 else ""
            thumb_1200 = eager_response[1].get("secure_url") if len(eager_response) > 1 else ""

            if thumb_600 and thumb_1200 and thumbnail_id:
                # Clean up old project thumbnail
                err = delete_image_file(project.thumbnail_id)
                if err:
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
        return redirect(url_for('home'), 303)

    return render_editor(project, form)


@app.route('/delete-project/<int:project_id>', methods=["POST"])
@limiter.limit("10 per minute")
@fresh_login_required
def delete_project(project_id):
    project = db.get_or_404(Project, project_id)

    # Clean up image
    err = delete_image_file(project.image_id)
    if err:
        flash(err, "error")
        return redirect(url_for('edit_project', project_id=project_id), 303)

    # Clean up thumbnail
    err = delete_image_file(project.thumbnail_id)
    if err:
        flash(err, "error")
        return redirect(url_for('edit_project', project_id=project_id), 303)

    # Commit to deletion
    db.session.delete(project)
    db.session.commit()

    current_app.logger.info("Admin %s deleted project %s", current_user.name, project.title)
    return redirect(url_for('home'))


@app.route('/')
def home():
    projects = db.session.execute(db.select(Project)).scalars().all()
    return render_template('index.html', projects=projects, current_user=current_user)


@app.route('/contact', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        email = EmailForm(
            form.name.data,
            form.email.data,
            form.reason.data,
            form.message.data,
            form.send_copy.data,
        )

        # Send email
        err_flash, err_log = email.send()
        if err_log or err_flash:
            if err_log: current_app.logger.error(err_log)
            if err_flash: flash(err_flash, "error")
            return render_template('contact.html', form=form)

        current_app.logger.info("Sent email from %s.", form.email.data)
        flash("Email sent successfully.", "success")
        return redirect(url_for('contact'), 303)
    return render_template('contact.html', form=form)


if __name__ == '__main__':
    port = int(env.get('PORT', 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
