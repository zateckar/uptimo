"""Stub cache service for compatibility.

This service previously provided caching functionality using Flask-Caching,
but caching has been disabled due to SQLAlchemy object serialization issues.
The service maintains API compatibility for existing code.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import current_app


class CacheService:
    """Stub service for caching operations - disabled for compatibility."""

    def __init__(self):
        self._enabled: bool = False
        # Cache is disabled - no initialization needed

    def _initialize_cache(self) -> None:
        """Initialize the caching backend (disabled)."""
        self._enabled = False
        current_app.logger.info("Cache service disabled - Flask-Caching removed")

    def is_enabled(self) -> bool:
        """Check if caching is enabled."""
        return False  # Always disabled

    def get_public_status_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached public status page data (always returns None)."""
        return None  # Cache miss - always fetch fresh data

    def set_public_status_data(
        self, cache_key: str, data: Dict[str, Any], timeout: int = 300
    ) -> bool:
        """Cache public status page data (always returns False - no caching)."""
        return False  # No caching performed

    def invalidate_public_status_cache(self, cache_key: str) -> bool:
        """Invalidate cached public status page data (no-op)."""
        return True  # Success - nothing to invalidate

    def get_cache_key(self, status_page_id: int, url_type: str) -> str:
        """Generate cache key for a public status page (returns key for compatibility)."""
        return f"public_status:{status_page_id}:{url_type}"

    def invalidate_monitor_cache(self, monitor_id: int) -> None:
        """Invalidate all caches that contain data for a specific monitor (no-op)."""
        pass  # No cache to invalidate

    def get_monitor_version_key(self, monitor_ids: list[int]) -> str:
        """Generate a version key based on monitor versions (returns timestamp)."""
        return str(datetime.now(timezone.utc).timestamp())

    def clear_all_public_status_cache(self) -> bool:
        """Clear all public status page caches (no-op)."""
        return True  # Success - nothing to clear

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "enabled": False,
            "message": "Flask-Caching has been removed - caching disabled",
        }

    def _make_serializable(self, obj: Any) -> Any:
        """Convert SQLAlchemy objects and other non-serializable items to serializable format.

        This method is kept for compatibility but is no longer used for caching.
        """
        # Handle SQLAlchemy model instances
        if hasattr(obj, "__tablename__") or (hasattr(obj, "_sa_instance_state")):
            # This is likely a SQLAlchemy model
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            else:
                # Manual serialization for SQLAlchemy objects
                result = {}
                for column in obj.__table__.columns:
                    value = getattr(obj, column.name)
                    if isinstance(value, (datetime,)):
                        result[column.name] = value.isoformat()
                    else:
                        result[column.name] = value
                return result
        elif isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (datetime,)):
            return obj.isoformat()
        else:
            return obj


# Global cache service instance (initialized lazily)
cache_service = None


def get_cache_service() -> CacheService:
    """Get the global cache service instance."""
    global cache_service
    if cache_service is None:
        cache_service = CacheService()
    return cache_service
