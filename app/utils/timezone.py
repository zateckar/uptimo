"""Timezone utilities for converting UTC times to user-configured timezone."""

from datetime import datetime, timezone
from typing import Optional, Union

import pytz
from pytz.tzinfo import DstTzInfo, StaticTzInfo


def get_app_timezone() -> Union[DstTzInfo, StaticTzInfo, pytz.UTC.__class__]:
    """Get the application's configured timezone.

    Returns:
        The configured timezone object, defaults to UTC if settings not available.
    """
    try:
        from app.models.app_settings import AppSettings

        settings = AppSettings.get_settings()
        tz_name = settings.timezone
        return pytz.timezone(tz_name)
    except Exception:
        return pytz.UTC


def utc_to_local(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert UTC datetime to the configured local timezone.

    Args:
        dt: UTC datetime object (timezone-aware or naive)

    Returns:
        Datetime converted to configured timezone, or None if input is None
    """
    if dt is None:
        return None

    # Ensure datetime is timezone-aware (assume UTC if naive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Get configured timezone
    local_tz = get_app_timezone()

    # Convert to local timezone
    return dt.astimezone(local_tz)


def format_datetime(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime in the configured local timezone.

    Args:
        dt: UTC datetime object
        fmt: Format string (default: "%Y-%m-%d %H:%M:%S")

    Returns:
        Formatted datetime string in local timezone, or "Never" if dt is None
    """
    if dt is None:
        return "Never"

    local_dt = utc_to_local(dt)
    if local_dt is None:
        return "Never"

    return local_dt.strftime(fmt)
