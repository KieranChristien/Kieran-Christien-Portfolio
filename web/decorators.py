from flask import current_app
from flask_login import current_user, fresh_login_required
from functools import wraps


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
            return current_app.login_manager.unauthorized()

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
    def decorated_view(admin_id, *args, **kwargs):
        if current_user.id != admin_id and not current_user.is_owner:
            return current_app.login_manager.unauthorized()

        return func(*args, **kwargs)

    return decorated_view
