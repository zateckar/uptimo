"""Template filters for the Uptimo application."""

from datetime import datetime, timezone
from typing import Optional

from app.utils.timezone import format_datetime, utc_to_local


def ago(dt: Optional[datetime]) -> str:
    """Format a datetime as a human-readable 'time ago' string."""
    if not dt:
        return "Never"

    # Ensure the datetime is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 2592000:  # 30 days
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 31536000:  # 1 year
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"


def local_time(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Convert UTC datetime to local timezone and format it.

    Args:
        dt: UTC datetime object
        fmt: Format string (default: "%Y-%m-%d %H:%M:%S")

    Returns:
        Formatted datetime string in local timezone
    """
    return format_datetime(dt, fmt)


def local_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert UTC datetime to local timezone datetime object.

    Args:
        dt: UTC datetime object

    Returns:
        Datetime object in local timezone
    """
    return utc_to_local(dt)


def register_filters(app) -> None:
    """Register all template filters with the Flask application."""
    app.add_template_filter(ago, "ago")
    app.add_template_filter(ago, "timeago")  # Alias for consistency
    app.add_template_filter(local_time, "local_time")
    app.add_template_filter(local_datetime, "local_datetime")
