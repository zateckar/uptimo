import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, TYPE_CHECKING

from app import db

if TYPE_CHECKING:
    from app.models.monitor import Monitor
    from app.models.incident import Incident


class NotificationType(Enum):
    """Notification type enumeration."""

    EMAIL = "email"
    TELEGRAM = "telegram"
    SLACK = "slack"


class NotificationChannel(db.Model):
    """Notification channel model for different alert delivery methods."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum(NotificationType), nullable=False)

    # Configuration stored as JSON
    config = db.Column(
        db.Text, nullable=False
    )  # JSON string with channel-specific config

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(
        db.Boolean, default=False, nullable=False
    )  # For channels that need verification
    last_sent = db.Column(db.DateTime)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    monitor_notifications = db.relationship(
        "MonitorNotification",
        backref="channel",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __init__(
        self,
        user_id: int,
        name: str,
        type: NotificationType,
        config: str,
        is_active: bool = True,
        is_verified: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.user_id = user_id
        self.name = name
        self.type = type
        self.config = config
        self.is_active = is_active
        self.is_verified = is_verified

    def get_config(self) -> Dict[str, Any]:
        """Parse and return configuration as dict."""
        try:
            return json.loads(self.config)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_config(self, config_dict: Dict[str, Any]) -> None:
        """Set configuration from dict."""
        self.config = json.dumps(config_dict)

    def send_notification(
        self,
        title: str,
        message: str,
        monitor: Optional["Monitor"] = None,
        incident: Optional["Incident"] = None,
    ) -> bool:
        """Send notification through this channel."""
        from app.notification.factory import NotificationFactory

        try:
            notifier = NotificationFactory.create_notifier(self.type)
            success = notifier.send(self, title, message, monitor, incident)

            if success:
                self.last_sent = datetime.now(timezone.utc)
                db.session.commit()

            return success
        except Exception as e:
            # Log error but don't raise to prevent breaking monitor checks
            print(f"Failed to send notification via {self.type}: {e}")
            return False

    def test_connection(self) -> bool:
        """Test connection to this notification channel."""
        from app.notification.factory import NotificationFactory

        try:
            notifier = NotificationFactory.create_notifier(self.type)
            return notifier.test_connection(self)
        except Exception as e:
            print(f"Failed to test connection for {self.type}: {e}")
            return False

    def __repr__(self) -> str:
        return f"<NotificationChannel {self.name} ({self.type.value})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification channel to dictionary for API responses."""
        config = self.get_config()
        # Remove sensitive information from config
        safe_config = {
            k: v
            for k, v in config.items()
            if k not in ["password", "token", "api_key", "webhook_url"]
        }

        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "config": safe_config,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_sent": self.last_sent.isoformat() if self.last_sent else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MonitorNotification(db.Model):
    """Associations between monitors and notification channels."""

    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(
        db.Integer, db.ForeignKey("monitor.id"), nullable=False, index=True
    )
    channel_id = db.Column(
        db.Integer, db.ForeignKey("notification_channel.id"), nullable=False, index=True
    )

    # Notification settings
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    notify_on_down = db.Column(db.Boolean, default=True, nullable=False)
    notify_on_up = db.Column(db.Boolean, default=True, nullable=False)
    notify_on_ssl_warning = db.Column(db.Boolean, default=True, nullable=False)

    # Delay settings
    consecutive_checks_threshold = db.Column(
        db.Integer, default=1
    )  # Send notification after N consecutive failures

    # Escalation settings
    escalate_after_minutes = db.Column(
        db.Integer
    )  # Escalate after X minutes of downtime

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Unique constraint to prevent duplicate monitor-channel pairs
    __table_args__ = (
        db.UniqueConstraint("monitor_id", "channel_id", name="uq_monitor_channel"),
        db.Index("idx_monitor_notification_monitor", "monitor_id"),
        db.Index("idx_monitor_notification_channel", "channel_id"),
    )

    def __init__(
        self,
        monitor_id: int,
        channel_id: int,
        is_enabled: bool = True,
        notify_on_down: bool = True,
        notify_on_up: bool = True,
        notify_on_ssl_warning: bool = True,
        consecutive_checks_threshold: int = 1,
        escalate_after_minutes: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.monitor_id = monitor_id
        self.channel_id = channel_id
        self.is_enabled = is_enabled
        self.notify_on_down = notify_on_down
        self.notify_on_up = notify_on_up
        self.notify_on_ssl_warning = notify_on_ssl_warning
        self.consecutive_checks_threshold = consecutive_checks_threshold
        self.escalate_after_minutes = escalate_after_minutes

    def should_notify(
        self, event_type: str, incident_duration_minutes: Optional[int] = None
    ) -> bool:
        """Check if notification should be sent for this event."""
        if not self.is_enabled:
            return False

        if event_type == "down" and self.notify_on_down:
            # Check escalation logic
            if self.escalate_after_minutes:
                return (
                    incident_duration_minutes >= self.escalate_after_minutes
                    if incident_duration_minutes is not None
                    else False
                )
            return True
        elif event_type == "up" and self.notify_on_up:
            return True
        elif event_type == "ssl_warning" and self.notify_on_ssl_warning:
            return True

        return False

    def __repr__(self) -> str:
        return (
            f"<MonitorNotification Monitor:{self.monitor_id} Channel:{self.channel_id}>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert monitor notification to dictionary for API responses."""
        return {
            "id": self.id,
            "monitor_id": self.monitor_id,
            "channel_id": self.channel_id,
            "is_enabled": self.is_enabled,
            "notify_on_down": self.notify_on_down,
            "notify_on_up": self.notify_on_up,
            "notify_on_ssl_warning": self.notify_on_ssl_warning,
            "consecutive_checks_threshold": self.consecutive_checks_threshold,
            "escalate_after_minutes": self.escalate_after_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NotificationLog(db.Model):
    """Log of sent notifications for audit and debugging."""

    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(
        db.Integer, db.ForeignKey("monitor.id"), nullable=False, index=True
    )
    channel_id = db.Column(
        db.Integer, db.ForeignKey("notification_channel.id"), nullable=False, index=True
    )
    incident_id = db.Column(
        db.Integer, db.ForeignKey("incident.id"), nullable=True, index=True
    )

    # Notification details
    event_type = db.Column(db.String(20), nullable=False)  # down, up, ssl_warning
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

    # Status
    sent_successfully = db.Column(db.Boolean, nullable=False)
    error_message = db.Column(db.Text)

    sent_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Indexes
    __table_args__ = (
        db.Index("idx_notification_log_monitor_sent", "monitor_id", "sent_at"),
        db.Index("idx_notification_log_channel_sent", "channel_id", "sent_at"),
        db.Index("idx_notification_log_status", "sent_successfully"),
    )

    def __init__(
        self,
        monitor_id: int,
        channel_id: int,
        event_type: str,
        title: str,
        message: str,
        sent_successfully: bool,
        incident_id: Optional[int] = None,
        error_message: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.monitor_id = monitor_id
        self.channel_id = channel_id
        self.event_type = event_type
        self.title = title
        self.message = message
        self.sent_successfully = sent_successfully
        self.incident_id = incident_id
        self.error_message = error_message

    def __repr__(self) -> str:
        return f"<NotificationLog {self.event_type} for Monitor {self.monitor_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification log to dictionary for API responses."""
        return {
            "id": self.id,
            "monitor_id": self.monitor_id,
            "channel_id": self.channel_id,
            "incident_id": self.incident_id,
            "event_type": self.event_type,
            "title": self.title,
            "message": self.message,
            "sent_successfully": self.sent_successfully,
            "error_message": self.error_message,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }
