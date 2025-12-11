"""Service layer for public status page functionality."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app import db
from app.models.check_result import CheckResult
from app.models.monitor import Monitor
from app.models.public_status_page import PublicStatusPage


class PublicStatusService:
    """Service class for public status page operations."""

    @staticmethod
    def get_active_status_page_by_uuid(uuid: str) -> Optional[PublicStatusPage]:
        """Get an active public status page by UUID."""
        return PublicStatusPage.query.filter(
            PublicStatusPage.uuid == uuid, PublicStatusPage.is_active.is_(True)
        ).first()

    @staticmethod
    def get_active_simple_status_page() -> Optional[PublicStatusPage]:
        """Get the active simple path status page."""
        return PublicStatusPage.query.filter(
            PublicStatusPage.url_type == "simple", PublicStatusPage.is_active.is_(True)
        ).first()

    @staticmethod
    def get_status_page_monitors(status_page: PublicStatusPage) -> List[Monitor]:
        """Get the monitors for a public status page."""
        try:
            monitor_ids = json.loads(status_page.selected_monitors)
            if not monitor_ids:
                return []

            return Monitor.query.filter(
                Monitor.id.in_(monitor_ids), Monitor.is_active.is_(True)
            ).all()
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def get_monitor_status_data(monitor: Monitor, hours: int = 24) -> Dict[str, Any]:
        """Get status data for a single monitor."""
        # Get recent check results
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        recent_checks = (
            CheckResult.query.filter(
                CheckResult.monitor_id == monitor.id,
                CheckResult.timestamp >= cutoff_time,
            )
            .order_by(CheckResult.timestamp.desc())
            .limit(100)
            .all()
        )

        # Get latest check for current status
        latest_check = (
            CheckResult.query.filter(CheckResult.monitor_id == monitor.id)
            .order_by(CheckResult.timestamp.desc())
            .first()
        )

        # Calculate uptime percentage
        total_checks = len(recent_checks)
        successful_checks = len([c for c in recent_checks if c.is_success()])
        uptime_percentage = (
            (successful_checks / total_checks * 100) if total_checks > 0 else 0
        )

        # Determine current status
        if not latest_check:
            status = "unknown"
            status_text = "Unknown"
        elif latest_check.is_success():
            status = "up"
            status_text = "Operational"
        else:
            status = "down"
            status_text = "Down"

        return {
            "id": monitor.id,
            "name": monitor.name,
            "type": monitor.type.value,
            "status": status,
            "status_text": status_text,
            "last_check": latest_check.timestamp if latest_check else None,
            "response_time": latest_check.response_time if latest_check else None,
            "uptime_percentage": round(uptime_percentage, 2),
            "total_checks": total_checks,
            "recent_checks": recent_checks[:50],  # Return CheckResult objects directly
        }

    @staticmethod
    def get_overall_status(monitors_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall system status from monitor data."""
        if not monitors_data:
            return {
                "status": "unknown",
                "status_text": "No monitors",
                "uptime_percentage": 0,
                "total_monitors": 0,
                "operational_monitors": 0,
                "down_monitors": 0,
                "unknown_monitors": 0,
            }

        total_monitors = len(monitors_data)
        operational_monitors = len([m for m in monitors_data if m["status"] == "up"])
        down_monitors = len([m for m in monitors_data if m["status"] == "down"])
        unknown_monitors = len([m for m in monitors_data if m["status"] == "unknown"])

        # Calculate overall uptime
        total_uptime = sum(m["uptime_percentage"] for m in monitors_data)
        overall_uptime = total_uptime / total_monitors if total_monitors > 0 else 0

        # Determine overall status
        if down_monitors > 0:
            status = "down"
            status_text = "System Issues"
        elif unknown_monitors > 0:
            status = "unknown"
            status_text = "Unknown Status"
        else:
            status = "up"
            status_text = "All Systems Operational"

        return {
            "status": status,
            "status_text": status_text,
            "uptime_percentage": round(overall_uptime, 2),
            "total_monitors": total_monitors,
            "operational_monitors": operational_monitors,
            "down_monitors": down_monitors,
            "unknown_monitors": unknown_monitors,
        }

    @staticmethod
    def get_heartbeat_data(
        monitors_data: List[Dict[str, Any]], hours: int = 6
    ) -> List[Dict[str, Any]]:
        """Get heartbeat data for the timeline visualization."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        heartbeats = []

        for monitor_data in monitors_data:
            monitor_id = monitor_data["id"]
            monitor_name = monitor_data["name"]

            # Get check results for heartbeat timeline
            check_results = (
                CheckResult.query.filter(
                    CheckResult.monitor_id == monitor_id,
                    CheckResult.timestamp >= cutoff_time,
                )
                .order_by(CheckResult.timestamp.desc())
                .limit(50)
                .all()
            )

            for check in check_results:
                heartbeats.append(
                    {
                        "monitor_id": monitor_id,
                        "monitor_name": monitor_name,
                        "timestamp": check.timestamp,
                        "status": "up" if check.is_success() else "down",
                        "response_time": check.response_time,
                    }
                )

        # Sort by timestamp (newest first for the display)
        heartbeats.sort(key=lambda x: x["timestamp"], reverse=True)
        return heartbeats

    @staticmethod
    def get_cached_public_status_data(status_page: PublicStatusPage) -> Dict[str, Any]:
        """Get public status page data (caching removed - always fetches fresh data)."""
        # Flask-Caching has been removed - always fetch fresh data
        # The performance impact is minimal for public pages which are typically low-traffic
        return PublicStatusService.format_public_status_data(status_page)

    @staticmethod
    def format_public_status_data(status_page: PublicStatusPage) -> Dict[str, Any]:
        """Format all data needed for a public status page."""
        # Get monitors for this status page
        monitors = PublicStatusService.get_status_page_monitors(status_page)

        # Get status data for each monitor
        monitors_data = [
            PublicStatusService.get_monitor_status_data(monitor) for monitor in monitors
        ]

        # Get overall status
        overall_status = PublicStatusService.get_overall_status(monitors_data)

        # Get heartbeat data for timeline
        heartbeat_data = PublicStatusService.get_heartbeat_data(monitors_data)

        return {
            "status_page": {
                "id": status_page.id,
                "custom_header": status_page.custom_header,
                "description": status_page.description,
                "url_type": status_page.url_type,
                "created_at": status_page.created_at,
            },
            "overall_status": overall_status,
            "monitors": monitors_data,
            "heartbeats": heartbeat_data,
            "last_updated": datetime.now(timezone.utc),
        }

    @staticmethod
    def validate_monitor_access(user_id: int, monitor_ids: List[int]) -> bool:
        """Validate that the user has access to all specified monitors."""
        if not monitor_ids:
            return True  # Empty selection is allowed (no monitors to validate)

        # Get all active monitors for the user
        user_monitors = Monitor.query.filter(
            Monitor.user_id == user_id, Monitor.is_active.is_(True)
        ).all()

        user_monitor_ids = [m.id for m in user_monitors]

        # Check if all requested monitors belong to the user
        return all(monitor_id in user_monitor_ids for monitor_id in monitor_ids)

    @staticmethod
    def create_status_page(
        user_id: int,
        url_type: str,
        selected_monitors: List[int],
        custom_header: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> PublicStatusPage:
        """Create a new public status page."""
        import secrets

        # Validate monitor access
        if not PublicStatusService.validate_monitor_access(user_id, selected_monitors):
            raise ValueError("Invalid monitor selection")

        # Check for simple path uniqueness
        if url_type == "simple":
            existing_simple = PublicStatusService.get_active_simple_status_page()
            if existing_simple:
                raise ValueError(
                    "A simple path status page already exists. Only one can be active."
                )

        status_page = PublicStatusPage(
            user_id=user_id,
            uuid=secrets.token_urlsafe(32),
            url_type=url_type,
            custom_header=custom_header,
            description=description,
            selected_monitors=selected_monitors,
            is_active=is_active,
        )

        db.session.add(status_page)
        db.session.commit()
        return status_page

    @staticmethod
    def update_status_page(
        status_page: PublicStatusPage,
        selected_monitors: List[int],
        custom_header: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Update an existing public status page."""
        # Validate monitor access
        if not PublicStatusService.validate_monitor_access(
            status_page.user_id, selected_monitors
        ):
            raise ValueError("Invalid monitor selection")

        status_page.custom_header = custom_header
        status_page.description = description
        status_page.selected_monitors = json.dumps(selected_monitors)

        db.session.commit()
        # Cache invalidation removed - Flask-Caching is no longer available

    @staticmethod
    def invalidate_status_page_cache(status_page: PublicStatusPage) -> None:
        """Invalidate cache for a specific status page (no-op - caching removed)."""
        # Cache invalidation removed - Flask-Caching is no longer available
        pass

    @staticmethod
    def invalidate_monitor_cache(monitor_id: int) -> None:
        """Invalidate cache for all status pages containing a specific monitor (no-op)."""
        # Cache invalidation removed - Flask-Caching is no longer available
        pass
