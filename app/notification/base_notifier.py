from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseNotifier(ABC):
    """Base class for all notification providers"""

    @abstractmethod
    def send(
        self,
        channel: Any,
        title: str,
        message: str,
        monitor: Optional[Any] = None,
        incident: Optional[Any] = None,
    ) -> bool:
        """Send notification through this channel"""
        pass

    @abstractmethod
    def test_connection(self, channel: Any) -> bool:
        """Test connection to this notification channel"""
        pass

    def format_message(
        self,
        title: str,
        message: str,
        monitor: Optional[Any] = None,
        incident: Optional[Any] = None,
    ) -> str:
        """Format the notification message with monitor and incident details"""
        formatted = f"{title}\n\n{message}"

        if monitor:
            formatted += "\n\nMonitor Details:\n"
            formatted += f"  • Name: {monitor.name}\n"
            formatted += f"  • Type: {monitor.type.value.upper()}\n"
            formatted += f"  • Target: {monitor.target}\n"
            formatted += f"  • Check Interval: {monitor.check_interval.value}s"

        if incident:
            formatted += "\n\nIncident Details:\n"
            formatted += f"  • Started: {incident.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            if incident.is_active():
                duration = incident.get_duration_formatted()
                formatted += f"  • Duration: {duration}\n"
            else:
                formatted += f"  • Resolved: {incident.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                formatted += f"  • Duration: {incident.get_duration_formatted()}\n"

        return formatted
