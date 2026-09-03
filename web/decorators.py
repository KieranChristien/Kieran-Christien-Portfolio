from flask import current_app, flash, redirect, url_for
from flask_login import current_user, fresh_login_required
from functools import wraps

from web.extensions import login_manager


def owner_required(func):
    """
    Require the currently authenticated user to be the owner.

    :param func: The view function to decorate.
    :type func: function
    """

    @wraps(func)
    @fresh_login_required
    def decorated_view(*args, **kwargs):
        if not current_user.is_owner:
            flash("Only owners can access this page.", "error")
            return redirect(url_for("auth.administration"), 303)

        return func(*args, **kwargs)

    return decorated_view


def self_or_owner_required(func):
    """
    Require the current user to be accessing their own account or to be an application owner.

    :param func: The view function to decorate.
    :type func: function
    """

    @wraps(func)
    @fresh_login_required
    def decorated_view(*args, **kwargs):
        admin_id = kwargs.get("admin_id")

        if admin_id is None:
            current_app.logger.error(
                "self_or_owner_required used on a route without admin_id: %s",
                func.__name__,
            )
            return login_manager.unauthorized()

        if current_user.id != admin_id and not current_user.is_owner:
            flash("Cannot access account that isn't yours.", "error")
            return redirect(url_for("auth.administration"), 303)

        return func(*args, **kwargs)

    return decorated_view
