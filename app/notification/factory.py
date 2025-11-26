from app.models.notification import NotificationType
from app.notification.email_notifier import EmailNotifier
from app.notification.telegram_notifier import TelegramNotifier
from app.notification.slack_notifier import SlackNotifier


class NotificationFactory:
    """Factory for creating notification providers"""

    _notifiers = {
        NotificationType.EMAIL: EmailNotifier,
        NotificationType.TELEGRAM: TelegramNotifier,
        NotificationType.SLACK: SlackNotifier,
    }

    @classmethod
    def create_notifier(cls, notification_type):
        """Create appropriate notifier instance"""
        notifier_class = cls._notifiers.get(notification_type)
        if not notifier_class:
            raise ValueError(f"Unsupported notification type: {notification_type}")

        return notifier_class()

    @classmethod
    def get_available_types(cls):
        """Get list of available notification types"""
        return list(cls._notifiers.keys())
