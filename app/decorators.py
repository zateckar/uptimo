"""Decorators for route protection and access control."""

from functools import wraps
from typing import Any, Callable

from flask import abort
from flask_login import current_user


def admin_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to require admin access for a route.

    Must be used after @login_required decorator.
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not current_user.is_authenticated:
            abort(403)
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function
