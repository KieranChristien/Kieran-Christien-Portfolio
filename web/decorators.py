from flask import current_app
from flask_login import current_user
from functools import wraps


def owner_required(func):
    """
    Require the currently authenticated user to be the owner.

    :param func: The view function to decorate.
    :type func: function
    """

    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.id == 1:
            return current_app.login_manager.unauthorized()

        return func(*args, **kwargs)

    return decorated_view
