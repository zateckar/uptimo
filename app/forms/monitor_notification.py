from wtforms import (
    SubmitField,
)
from app.models.notification import NotificationChannel
from app import db


class FormField:
    """Simple class to hold form field data."""

    def __init__(self, data: bool | int | list[str] | None = None):
        self.data: bool | int | list[str] | None = data


class MonitorNotificationForm:
    """Form class for managing monitor notification settings."""

    def __init__(self, monitor=None, user=None):
        """Initialize the form with monitor and user context."""
        self.monitor = monitor
        self.user = user
        self.channels = self._get_available_channels()

        # Initialize form fields
        self.channel_options = [(str(c.id), c.name) for c in self.channels]

        # Initialize default values with FormField objects
        self.channel_ids = FormField([])
        self.notify_on_down = FormField(True)
        self.notify_on_up = FormField(True)
        self.notify_on_ssl_warning = FormField(True)
        self.consecutive_checks_threshold = FormField(1)
        self.escalate_after_minutes = FormField(None)

        # Load existing settings if monitor is provided
        if monitor:
            self._load_existing_settings()

    def _get_available_channels(self):
        """Get available notification channels for the user."""
        if not self.user:
            return []
        return NotificationChannel.query.filter_by(
            user_id=self.user.id, is_active=True
        ).all()

    def _load_existing_settings(self):
        """Load existing notification settings for the monitor."""
        if not self.monitor:
            return

        # Get current notification settings
        settings = self.monitor.notification_settings.all()

        if settings:
            # Load channel IDs
            self.channel_ids.data = [str(s.channel_id) for s in settings]

            # Use first setting for common fields (they should be consistent)
            first_setting = settings[0]
            self.notify_on_down.data = first_setting.notify_on_down
            self.notify_on_up.data = first_setting.notify_on_up
            self.notify_on_ssl_warning.data = first_setting.notify_on_ssl_warning
            self.consecutive_checks_threshold.data = (
                first_setting.consecutive_checks_threshold
            )
            self.escalate_after_minutes.data = first_setting.escalate_after_minutes

    def validate(self):
        """Validate the form data."""
        errors = []

        # Check if at least one channel is selected
        if not self.channel_ids.data:
            errors.append("At least one notification channel must be selected")

        # Validate consecutive checks threshold
        threshold_data = self.consecutive_checks_threshold.data
        if isinstance(threshold_data, int) and (threshold_data < 1 or threshold_data > 10):
            errors.append("Consecutive checks threshold must be between 1 and 10")

        # Validate escalation logic
        escalate_data = self.escalate_after_minutes.data
        if isinstance(escalate_data, int) and escalate_data <= 0:
            errors.append("Escalation time must be greater than 0")

        return len(errors) == 0, errors

    def save_settings(self, monitor):
        """Save notification settings for the monitor."""
        if not self.validate()[0]:
            return False, "Validation failed"

        channel_ids_data = self.channel_ids.data
        selected_channel_ids: list[str] = (
            channel_ids_data if isinstance(channel_ids_data, list) else []
        )

        # Delete existing settings for channels not selected
        existing_settings = monitor.notification_settings.all()
        for setting in existing_settings:
            if str(setting.channel_id) not in selected_channel_ids:
                db.session.delete(setting)

        # Add or update settings for selected channels
        for channel_id in selected_channel_ids:
            channel_id_int = int(channel_id)

            # Check if setting already exists
            existing = monitor.notification_settings.filter_by(
                channel_id=channel_id_int
            ).first()

            if existing:
                # Update existing setting
                existing.notify_on_down = bool(self.notify_on_down.data) if self.notify_on_down.data is not None else True
                existing.notify_on_up = bool(self.notify_on_up.data) if self.notify_on_up.data is not None else True
                existing.notify_on_ssl_warning = bool(self.notify_on_ssl_warning.data) if self.notify_on_ssl_warning.data is not None else True
                existing.consecutive_checks_threshold = (
                    int(self.consecutive_checks_threshold.data) if isinstance(self.consecutive_checks_threshold.data, int) else 1
                )
                existing.escalate_after_minutes = int(self.escalate_after_minutes.data) if isinstance(self.escalate_after_minutes.data, int) else None
            else:
                # Create new setting
                from app.models.notification import MonitorNotification

                new_setting = MonitorNotification(
                    monitor_id=monitor.id,
                    channel_id=channel_id_int,
                    is_enabled=True,
                    notify_on_down=bool(self.notify_on_down.data) if self.notify_on_down.data is not None else True,
                    notify_on_up=bool(self.notify_on_up.data) if self.notify_on_up.data is not None else True,
                    notify_on_ssl_warning=bool(self.notify_on_ssl_warning.data) if self.notify_on_ssl_warning.data is not None else True,
                    consecutive_checks_threshold=(
                        int(self.consecutive_checks_threshold.data) if isinstance(self.consecutive_checks_threshold.data, int) else 1
                    ),
                    escalate_after_minutes=int(self.escalate_after_minutes.data) if isinstance(self.escalate_after_minutes.data, int) else None,
                )
                db.session.add(new_setting)

        db.session.commit()
        return True, "Notification settings updated successfully"


class MonitorNotificationEditForm(MonitorNotificationForm):
    """Form for editing existing monitor notification settings."""

    submit = SubmitField("Save Changes")
