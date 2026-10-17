import pyotp
from flask import (Blueprint, after_this_request, current_app, flash, redirect, render_template, request, session,
                   url_for, )
from flask_login import current_user, login_user, login_required, logout_user, fresh_login_required
from sqlalchemy.exc import IntegrityError
from urllib.parse import urljoin, urlparse
from werkzeug.security import generate_password_hash, check_password_hash

from web.decorators import owner_required, self_or_owner_required
from web.extensions import db, limiter, login_manager
from web.forms import DisableTwoFactorForm, EditAdminForm, LoginAdminForm, RegisterAdminForm, TwoFactorCodeForm
from web.models import Admin
from web.two_factor import (decrypt_totp_secret, encrypt_totp_secret, generate_recovery_codes, make_qr_data_uri,
                            matching_totp_step, verify_totp_or_recovery_code, )

auth = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(user_id):
    try:
        uid: int = int(user_id)
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


def render_editor(form, admin: Admin | None = None, is_edit: bool = False, status_code=200) -> tuple[str, int]:
    return render_template(
        "auth/admin_editor.html",
        admin=admin,
        form=form,
        current_user=current_user,
        is_edit=is_edit
    ), status_code


def flash_and_render_editor(message: str, category: str, form, admin: Admin | None = None, is_edit: bool = False,
                            status_code=200) -> tuple[str, int]:
    flash(message, category)
    return render_editor(form=form, admin=admin, is_edit=is_edit, status_code=status_code)


def _set_no_store_headers() -> None:
    """Prevent caching of pages containing secrets or recovery codes."""

    @after_this_request
    def add_no_store_headers(response):
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, private"
        )
        response.headers["Pragma"] = "no-cache"
        return response


def _render_two_factor_settings(
        admin: Admin,
        recovery_codes=None,
):
    """Render the user's 2FA settings and enrollment QR code."""
    _set_no_store_headers()

    secret = None
    qr_data_uri = None

    if not admin.totp_enabled:
        # Create a seed on first visit to the setup page.
        if not admin.totp_secret:
            admin.totp_secret = encrypt_totp_secret(
                pyotp.random_base32()
            )
            db.session.commit()

        secret = decrypt_totp_secret(
            admin.totp_secret
        )

        provisioning_uri = pyotp.TOTP(
            secret
        ).provisioning_uri(
            name=admin.email,
            issuer_name=current_app.config.get(
                "TOTP_ISSUER",
                "Kieran Christien Portfolio",
            ),
        )

        qr_data_uri = make_qr_data_uri(
            provisioning_uri
        )

    return render_template(
        "auth/two_factor.html",
        current_user=current_user,
        code_form=TwoFactorCodeForm(),
        disable_form=DisableTwoFactorForm(),
        secret=secret,
        qr_data_uri=qr_data_uri,
        recovery_codes=recovery_codes,
    )


# Register new admins into the Admin database
@auth.route('/admin/register', methods=["GET", "POST"])
@limiter.limit("10 per minute")
@owner_required
def register():
    form = RegisterAdminForm()
    if form.validate_on_submit():
        # Check if admin email is already present in the database.
        email = form.email.data.strip().lower()
        existing_admin = db.session.execute(db.select(Admin).where(Admin.email == email)).scalar_one_or_none()
        if existing_admin:
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
            return flash_and_render_editor(
                "Unable to register. Please try again.",
                "error",
                form,
                status_code=409
            )

        current_app.logger.info("Admin %s registered by %s.", new_admin.name, current_user.name)
        return redirect(url_for("auth.administration"), 303)
    return render_editor(form)


# Edit existing admin's details
@auth.route('/admin/edit/<int:admin_id>', methods=["GET", "POST"])
@limiter.limit("10 per minute")
@self_or_owner_required
def edit(admin_id):
    current_admin = db.get_or_404(Admin, admin_id)
    form = EditAdminForm(
        name=current_admin.name,
        email=current_admin.email,
    )

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        has_changes = form.name.data != current_admin.name or email != current_admin.email or bool(form.password.data)

        if not has_changes:
            return flash_and_render_editor(
                "No changes made.",
                "error",
                form,
                current_admin,
                True
            )

        if form.name.data != current_admin.name:
            current_admin.name = form.name.data

        if email != current_admin.email:
            existing_email = db.session.execute(db.select(Admin).where(
                Admin.email == email,
                Admin.id != current_admin.id,
            )).scalar_one_or_none()

            if existing_email:
                return flash_and_render_editor(
                    "That email address is already in use.",
                    "error",
                    form,
                    current_admin,
                    True,
                )

            current_admin.email = email

        if form.password.data:
            current_admin.password = generate_password_hash(
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
                form,
                current_admin,
                True,
                409
            )

        current_app.logger.info("Admin %s edited %s's account.", current_user.name, current_admin.name)
        return redirect(url_for("auth.administration"), 303)
    return render_editor(form, current_admin, True)


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

    current_admin = db.get_or_404(Admin, admin_id)

    actor_name = current_user.name
    target_name = current_admin.name

    db.session.delete(current_admin)
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
    return redirect(url_for('auth.administration'))


# Login admin
@auth.route('/admin/login', methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    form = LoginAdminForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        admin_to_login = db.session.execute(db.select(Admin).where(Admin.email == email)).scalar_one_or_none()

        # Email doesn't exist or password incorrect
        if not admin_to_login or not check_password_hash(admin_to_login.password, password):
            current_app.logger.info("Failed login attempt for %s.", email)
            flash("Email or password incorrect, please try again.", "error")
            return render_template("auth/login.html", form=form, current_user=current_user)

        # Determine where the user should go after login.
        next_page = request.args.get("next", "")

        if not next_page or not is_safe_url(next_page):
            next_page = url_for("auth.administration")

        # Clear pre-authentication session state.
        session.clear()

        if admin_to_login.totp_enabled:
            # The user is not authenticated yet.
            # Store only a pending user ID until factor two succeeds.
            session["pending_2fa_user_id"] = admin_to_login.id
            session["pending_2fa_next"] = next_page

            current_app.logger.info(
                "Password accepted; awaiting second factor "
                "for admin id %s.",
                admin_to_login.id,
            )

            return redirect(
                url_for("auth.verify_two_factor"),
                303,
            )

        # Accounts without 2FA retain the existing login flow.
        login_user(admin_to_login, fresh=True)

        current_app.logger.info(
            "%s logged in.",
            admin_to_login.name,
        )

        return redirect(next_page, 303)

    return render_template("auth/login.html", form=form, current_user=current_user)


@auth.route("/admin/two-factor", methods=["GET"])
@fresh_login_required
def two_factor():
    """Display authenticator setup and account security settings."""
    admin = db.session.get(Admin, current_user.id)

    if not admin:
        logout_user()
        return redirect(url_for("auth.login"), 303)

    return _render_two_factor_settings(admin)


@auth.route("/admin/two-factor/enable", methods=["POST"])
@limiter.limit("5 per minute")
@fresh_login_required
def enable_two_factor():
    """Enable 2FA only after the user proves possession of the seed."""
    admin = db.session.get(Admin, current_user.id)
    form = TwoFactorCodeForm()

    if (
            not admin
            or admin.totp_enabled
            or not admin.totp_secret
    ):
        flash(
            "Start setup from the two-factor authentication "
            "page and try again.",
            "error",
        )
        return redirect(url_for("auth.two_factor"), 303)

    if not form.validate_on_submit():
        flash(
            "Enter the six-digit code from your authenticator app.",
            "error",
        )
        return redirect(url_for("auth.two_factor"), 303)

    secret = decrypt_totp_secret(admin.totp_secret)

    step = matching_totp_step(
        secret,
        form.code.data,
    )

    if step is None:
        flash(
            "That authenticator code is invalid or expired. "
            "Try the latest code.",
            "error",
        )
        return redirect(url_for("auth.two_factor"), 303)

    # Generate recovery codes only after successful enrollment.
    recovery_codes, hashed_recovery_codes = (
        generate_recovery_codes()
    )

    admin.totp_enabled = True
    admin.totp_last_used_step = step
    admin.totp_recovery_codes = hashed_recovery_codes

    db.session.commit()

    current_app.logger.info(
        "Two-factor authentication enabled for admin id %s.",
        admin.id,
    )

    flash(
        "Two-factor authentication is enabled. "
        "Save the recovery codes below now.",
        "success",
    )

    # Display plaintext recovery codes in this response only.
    return _render_two_factor_settings(
        admin,
        recovery_codes=recovery_codes,
    )


@auth.route("/admin/two-factor/disable", methods=["POST"])
@limiter.limit("5 per minute")
@fresh_login_required
def disable_two_factor():
    """Disable 2FA only after password and factor verification."""
    admin = db.session.get(Admin, current_user.id)
    form = DisableTwoFactorForm()

    if not admin or not admin.totp_enabled:
        flash(
            "Two-factor authentication is not enabled.",
            "notice",
        )
        return redirect(url_for("auth.two_factor"), 303)

    if not form.validate_on_submit():
        flash(
            "Enter your current password and an authenticator "
            "or recovery code.",
            "error",
        )
        return redirect(url_for("auth.two_factor"), 303)

    # Require the current password.
    if not check_password_hash(
            admin.password,
            form.password.data,
    ):
        current_app.logger.warning(
            "Invalid password during 2FA disable "
            "for admin id %s.",
            admin.id,
        )

        flash(
            "Unable to disable two-factor authentication "
            "with those details.",
            "error",
        )
        return redirect(url_for("auth.two_factor"), 303)

    # Also require and validate the second factor.
    if not verify_totp_or_recovery_code(
            admin,
            form.code.data,
    ):
        current_app.logger.warning(
            "Invalid second factor during 2FA disable "
            "for admin id %s.",
            admin.id,
        )

        flash(
            "Unable to disable two-factor authentication "
            "with those details.",
            "error",
        )
        return redirect(url_for("auth.two_factor"), 303)

    admin.totp_enabled = False
    admin.totp_secret = None
    admin.totp_recovery_codes = None
    admin.totp_last_used_step = None

    db.session.commit()

    current_app.logger.info(
        "Two-factor authentication disabled for admin id %s.",
        admin.id,
    )

    flash(
        "Two-factor authentication has been disabled.",
        "success",
    )

    return redirect(url_for("auth.two_factor"), 303)


@auth.route("/admin/login/2fa", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def verify_two_factor():
    """Complete login after password verification and TOTP."""
    _set_no_store_headers()

    pending_user_id = session.get("pending_2fa_user_id")

    admin: Admin | None = (
        db.session.get(Admin, pending_user_id)
        if pending_user_id is not None
        else None
    )

    # Do not accept a stale or invalid pending login.
    if not admin or not admin.totp_enabled:
        session.clear()

        flash(
            "Please log in again to continue.",
            "notice",
        )

        return redirect(url_for("auth.login"), 303)

    form = TwoFactorCodeForm()

    if form.validate_on_submit():
        if verify_totp_or_recovery_code(
                admin,
                form.code.data,
        ):
            # Persist used TOTP steps or consumed recovery codes
            # before granting the authenticated session.
            db.session.commit()

            next_page = session.get(
                "pending_2fa_next",
                "",
            )

            # Remove temporary pre-authentication state.
            session.clear()

            # Authenticate only after factor two succeeds.
            login_user(admin, fresh=True)

            if not next_page or not is_safe_url(next_page):
                next_page = url_for("auth.administration")

            current_app.logger.info(
                "%s logged in with two-factor authentication.",
                admin.name,
            )

            return redirect(next_page, 303)

        current_app.logger.warning(
            "Invalid second factor during login "
            "for admin id %s.",
            admin.id,
        )

        flash(
            "That code is invalid, expired, or already used. "
            "Try again.",
            "error",
        )

    return render_template(
        "auth/two_factor_verify.html",
        form=form,
        current_user=current_user,
    )


@auth.route('/admin/logout', methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def logout():
    current_app.logger.info("%s logged out.", current_user.name)
    logout_user()
    return redirect(url_for('main.home'), 303)


@auth.route('/admin')
@fresh_login_required
def administration():
    admins = db.session.execute(db.select(Admin)).scalars().all()

    return render_template("auth/admin.html", admins=admins, current_user=current_user)
