from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, login_required, logout_user
from sqlalchemy.exc import IntegrityError
from urllib.parse import urljoin, urlparse
from werkzeug.security import generate_password_hash, check_password_hash

from web.decorators import owner_required, self_or_owner_required
from web.extensions import db, limiter, login_manager
from web.forms import EditAdminForm, LoginAdminForm, RegisterAdminForm
from web.models import Admin

auth = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(Admin, uid)


def is_safe_url(target: str) -> bool:
    """
    Check if target url is local.
    :param target:
    :return:
    """
    host_url = urlparse(request.host_url)
    target_url = urlparse(urljoin(request.host_url, target))

    return target_url.scheme in ("http", "https") and host_url.netloc == target_url.netloc


def render_editor(admin, form, status_code=200):
    return render_template(
        "admin_editor.html",
        admin=admin,
        form=form,
        current_user=current_user,
        is_edit=True
    ), status_code


def flash_and_render_editor(message, category, admin, form, status_code=200):
    flash(message, category)
    return render_editor(admin, form, status_code)


# Register new admins into the Admin database
@auth.route('/admin/register', methods=["GET", "POST"])
@limiter.limit("10 per minute")
@owner_required
def register():
    form = RegisterAdminForm()
    if form.validate_on_submit():
        # Check if admin email is already present in the database.
        email = form.email.data.strip().lower()
        admin = db.session.execute(db.select(Admin).where(Admin.email == email)).scalar_one_or_none()
        if admin:
            # Admin already exists
            current_app.logger.info("Sign up attempt for existing email %s. Redirecting to login page.", email)
            flash("You've already signed up with that email, log in instead!", "info")
            return redirect(url_for('auth.login'), 303)

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=16
        )
        new_admin = Admin()
        new_admin.email = email
        new_admin.name = form.name.data
        new_admin.password = hash_and_salted_password
        new_admin.is_owner = False

        db.session.add(new_admin)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

            current_app.logger.exception("Failed to register admin %s.", new_admin.email)
            flash("Unable to register. Please try again.","error")
            return render_template("admin_editor.html", form=form, current_user=current_user), 409

        # This line will authenticate the admin with Flask-Login
        login_user(new_admin)

        current_app.logger.info("Admin %s signed up.", new_admin.name)
        return redirect(url_for("main.home"), 303)
    return render_template("admin_editor.html", form=form, current_user=current_user)


# Edit existing admin's details
@auth.route('/admin/edit/<int:admin_id>', methods=["GET", "POST"])
@limiter.limit("10 per minute")
@self_or_owner_required
def edit(admin_id):
    admin = db.get_or_404(Admin, admin_id)
    form = EditAdminForm(
        name=admin.name,
        email=admin.email,
    )
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        has_changes = form.name.data != admin.name or email != admin.email or bool(form.password.data)

        if not has_changes:
            return flash_and_render_editor("No changes made.", "error", admin, form)

        if form.name.data != admin.name:
            admin.name = form.name.data

        if email != admin.email:
            existing_email = db.session.execute(db.select(Admin).where(
                Admin.email == email,
                Admin.id != admin.id,
            )).scalar_one_or_none()

            if existing_email:
                return flash_and_render_editor(
                    "That email address is already in use.",
                    "error",
                    admin,
                    form
                )

            admin.email = email

        if form.password.data:
            admin.password = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256',
                salt_length=16
            )

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

            current_app.logger.exception("Failed to edit admin %s.", admin_id)
            return flash_and_render_editor(
                "Unable to save your changes. Please try again.",
                "error",
                admin,
                form,
                409
            )

        current_app.logger.info(f"Admin %s edited %s's account.", current_user.name, admin.name)
        return redirect(url_for("main.home"), 303)
    return render_editor(admin, form)


# Delete existing admin
@auth.route('/admin/delete/<int:admin_id>', methods=["POST"])
@limiter.limit("10 per minute")
@self_or_owner_required
def delete(admin_id):
    is_self = current_user.id == admin_id

    if is_self and current_user.is_owner:
        has_another_owner = db.session.execute(
            db.select(Admin)
            .where(
                Admin.is_owner.is_(True),
                Admin.id != current_user.id,
            )
            .limit(1)
        ).first()

        if not has_another_owner:
            flash("Cannot delete only existing owner account.", "error")
            return redirect(url_for("auth.edit", admin_id=admin_id))

    admin = db.get_or_404(Admin, admin_id)

    actor_name = current_user.name
    target_name = admin.name

    db.session.delete(admin)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to delete admin %s.",
            admin_id,
        )

        flash("Unable to delete the account. Please try again.", "error")
        return redirect(url_for("auth.edit", admin_id=admin_id))

    if is_self:
        logout_user()

    current_app.logger.info("Admin %s deleted %s's account.", actor_name, target_name)
    return redirect(url_for('main.home'))


# Login admin
@auth.route('/admin/login', methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    form = LoginAdminForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        admin = db.session.execute(db.select(Admin).where(Admin.email == email)).scalar_one_or_none()

        # Email doesn't exist or password incorrect
        if not admin or not check_password_hash(admin.password, password):
            current_app.logger.info("Failed login attempt for %s.", email)
            flash("Email or password incorrect, please try again.", "error")
            return render_template("login.html", form=form, current_user=current_user)

        login_user(admin)

        # Get the page the user was trying to access
        next_page = request.args.get('next', '')

        if not next_page or not is_safe_url(next_page):
            next_page = url_for('main.home')

        current_app.logger.info("%s logged in.", admin.name)
        return redirect(next_page, 303)

    return render_template("login.html", form=form, current_user=current_user)


@auth.route('/admin/logout', methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def logout():
    current_app.logger.info("%s logged out.", current_user.name)
    logout_user()
    return redirect(url_for('main.home'), 303)
