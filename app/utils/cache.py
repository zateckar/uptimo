"""Simple caching utilities for performance optimization."""

from functools import wraps
from flask import make_response
from datetime import datetime, timedelta


def static_cache(func):
    """Simple caching decorator for static assets.

    Provides 1-year cache for immutable static assets like CSS, JS, images.
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        response = make_response(func(*args, **kwargs))

        # 1 year cache for static assets (immutable content)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        # Add expiration header
        from datetime import timezone

        expires = datetime.now(timezone.utc) + timedelta(days=365)
        response.headers["Expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

        # Add ETag for conditional requests
        response.add_etag()

        return response

    return decorated_function


def api_cache(max_age=30):
    """Simple API caching decorator for non-critical endpoints.

    Args:
        max_age: Cache duration in seconds (default: 30)
    """

    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            response = make_response(func(*args, **kwargs))

            # Short cache for API responses
            response.headers["Cache-Control"] = "private, max-age={}".format(max_age)
            response.add_etag()

            return response

        return decorated_function

    return decorator
