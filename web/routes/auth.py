from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, login_required, logout_user, fresh_login_required
from urllib.parse import urljoin, urlparse
from werkzeug.security import generate_password_hash, check_password_hash

from web.decorators import owner_required
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


# Register new admins into the Admin database
@auth.route('/admin/register', methods=["GET", "POST"])
@limiter.limit("10 per minute")
@fresh_login_required
@owner_required
def register():
    form = RegisterAdminForm()
    if form.validate_on_submit():
        # Check if admin email is already present in the database.
        result = db.session.execute(db.select(Admin).where(Admin.email == form.email.data))
        user = result.scalar()
        if user:
            # Admin already exists
            current_app.logger.info(f"Sign up attempt for existing email {form.email.data}. Redirecting to login page.")
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('auth.login'), 303)

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
        return redirect(url_for("main.home"), 303)
    return render_template("admin_editor.html", form=form, current_user=current_user)


# Edit existing admin's details
@auth.route('/admin/edit/<int:admin_id>', methods=["GET", "POST"])
@limiter.limit("10 per minute")
@fresh_login_required
def edit(admin_id):
    # Prevent anyone other than the admin and owner from editing the admin's details
    if current_user.id != admin_id and current_user.id != 1:
        return current_app.login_manager.unauthorized()

    admin = db.get_or_404(Admin, admin_id)
    form = EditAdminForm(
        name=admin.name,
        email=admin.email,
    )
    if form.validate_on_submit():
        hashed_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=16
        )
        changed = form.name.data != admin.name or form.email.data != admin.email or (form.password.data and hashed_password != admin.password)

        if not changed:
            flash("No changes made.", "error")
            return render_template("admin_editor.html", admin=admin, form=form, current_user=current_user, is_edit=True)

        if form.name.data != admin.name:
            admin.name = form.name.data

        if form.email.data != admin.email:
            admin.email = form.email.data

        if form.password.data:
            admin.password = hashed_password

        db.session.commit()

        current_app.logger.info(f"Admin {current_user.name} edited {admin.name}'s account.")
        return redirect(url_for("main.home"), 303)
    return render_template("admin_editor.html", admin=admin, form=form, current_user=current_user, is_edit=True)


# Delete existing admin
@auth.route('/admin/delete/<int:admin_id>', methods=["POST"])
@limiter.limit("10 per minute")
@fresh_login_required
def delete(admin_id):
    # Prevent anyone other than the admin and owner from deleting the admin
    if current_user.id != admin_id and current_user.id != 1:
        return current_app.login_manager.unauthorized()

    admin = db.get_or_404(Admin, admin_id)

    db.session.delete(admin)
    db.session.commit()

    current_app.logger.info("Admin %s deleted %s's account.", current_user.name, admin.name)
    return redirect(url_for('main.home'))


# Login admin
@auth.route('/admin/login', methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    form = LoginAdminForm()
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
                next_page = url_for('main.home')

            current_app.logger.info(f"Admin {user.name} logged in.")
            return redirect(next_page, 303)

    return render_template("login.html", form=form, current_user=current_user)


@auth.route('/admin/logout', methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def logout():
    current_app.logger.info(f"Admin {current_user.name} logged out.")
    logout_user()
    return redirect(url_for('main.home'), 303)
