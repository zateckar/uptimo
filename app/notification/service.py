import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app import db
from app.models.notification import (
    NotificationChannel,
    NotificationLog,
    MonitorNotification,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications"""

    def send_monitor_notification(
        self,
        monitor: Any,
        event_type: str,
        title: str,
        message: str,
        incident: Optional[Any] = None,
    ) -> bool:
        """Send notification for a monitor event"""
        try:
            # Get all notification settings for this monitor
            monitor_notifications = MonitorNotification.query.filter_by(
                monitor_id=monitor.id, is_enabled=True
            ).all()

            sent_count = 0
            error_count = 0

            for monitor_notification in monitor_notifications:
                try:
                    channel = monitor_notification.channel

                    # Check if channel is active
                    if not channel.is_active:
                        logger.warning(f"Skipping inactive channel {channel.id}")
                        continue

                    # Check consecutive failures threshold for down notifications
                    if event_type == "down":
                        threshold = (
                            monitor_notification.consecutive_checks_threshold or 1
                        )
                        consecutive = monitor.consecutive_failures or 0
                        if consecutive < threshold:
                            logger.debug(
                                f"Skipping notification for channel {channel.id}: "
                                f"consecutive failures ({consecutive}) below "
                                f"threshold ({threshold})"
                            )
                            continue

                    # Check if we should notify for this event
                    incident_duration = None
                    if incident and incident.is_active():
                        incident_duration = (
                            datetime.now(timezone.utc) - incident.started_at
                        ).total_seconds() / 60

                    if not monitor_notification.should_notify(
                        event_type, incident_duration
                    ):
                        logger.debug(
                            f"Skipping notification for channel {channel.id} "
                            f"based on settings"
                        )
                        continue

                    # Send notification
                    success = channel.send_notification(
                        title, message, monitor, incident
                    )

                    # Log notification
                    notification_log = NotificationLog(
                        monitor_id=monitor.id,
                        channel_id=channel.id,
                        incident_id=incident.id if incident else None,
                        event_type=event_type,
                        title=title,
                        message=message,
                        sent_successfully=success,
                        error_message=None
                        if success
                        else "Failed to send notification",
                    )
                    db.session.add(notification_log)

                    if success:
                        sent_count += 1
                        logger.info(
                            f"Notification sent successfully via {channel.type.value} for monitor {monitor.name}"
                        )
                    else:
                        error_count += 1
                        logger.error(
                            f"Failed to send notification via {channel.type.value} for monitor {monitor.name}"
                        )

                except Exception as e:
                    error_count += 1
                    logger.error(
                        f"Error sending notification for monitor {monitor.id}: {e}"
                    )

                    # Log error
                    try:
                        notification_log = NotificationLog(
                            monitor_id=monitor.id,
                            channel_id=monitor_notification.channel_id,
                            incident_id=incident.id if incident else None,
                            event_type=event_type,
                            title=title,
                            message=message,
                            sent_successfully=False,
                            error_message=str(e),
                        )
                        db.session.add(notification_log)
                    except Exception:
                        pass

            # Commit all notification logs
            try:
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to commit notification logs: {e}")
                db.session.rollback()

            logger.info(
                f"Notification summary for monitor {monitor.name}: {sent_count} sent, {error_count} errors"
            )
            return sent_count > 0

        except Exception as e:
            logger.error(f"Error in send_monitor_notification: {e}")
            return False

    def get_notification_history(
        self,
        monitor_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Any:
        """Get notification history with filters"""
        query = NotificationLog.query

        # Apply filters
        if monitor_id:
            query = query.filter(NotificationLog.monitor_id == monitor_id)

        if channel_id:
            query = query.filter(NotificationLog.channel_id == channel_id)

        if event_type:
            query = query.filter(NotificationLog.event_type == event_type)

        if start_date:
            query = query.filter(NotificationLog.sent_at >= start_date)

        if end_date:
            query = query.filter(NotificationLog.sent_at <= end_date)

        # Order by most recent first
        query = query.order_by(NotificationLog.sent_at.desc())

        # Paginate
        notifications = query.paginate(page=page, per_page=per_page, error_out=False)

        return notifications

    def get_notification_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get notification statistics for the last N days"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Total notifications
        total_notifications = NotificationLog.query.filter(
            NotificationLog.sent_at >= start_date
        ).count()

        # Successful notifications
        successful_notifications = NotificationLog.query.filter(
            NotificationLog.sent_at >= start_date,
            NotificationLog.sent_successfully,
        ).count()

        # Failed notifications
        failed_notifications = total_notifications - successful_notifications

        # By event type
        event_type_stats = {}
        event_types = (
            db.session.query(
                NotificationLog.event_type,
                db.func.count(NotificationLog.id).label("count"),
            )
            .filter(NotificationLog.sent_at >= start_date)
            .group_by(NotificationLog.event_type)
            .all()
        )

        for event_type, count in event_types:
            event_type_stats[event_type] = count

        # By channel type
        channel_type_stats = {}
        channel_types = (
            db.session.query(
                NotificationChannel.type,
                db.func.count(NotificationLog.id).label("count"),
            )
            .join(NotificationChannel)
            .filter(NotificationLog.sent_at >= start_date)
            .group_by(NotificationChannel.type)
            .all()
        )

        for channel_type, count in channel_types:
            channel_type_stats[channel_type.value] = count

        return {
            "period_days": days,
            "total_notifications": total_notifications,
            "successful_notifications": successful_notifications,
            "failed_notifications": failed_notifications,
            "success_rate": round(
                (successful_notifications / total_notifications * 100), 2
            )
            if total_notifications > 0
            else 0,
            "by_event_type": event_type_stats,
            "by_channel_type": channel_type_stats,
        }

    def cleanup_old_notification_logs(self, days_to_keep: int = 90) -> int:
        """Clean up old notification logs"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

            deleted_count = NotificationLog.query.filter(
                NotificationLog.sent_at < cutoff_date
            ).delete()

            db.session.commit()

            logger.info(f"Cleaned up {deleted_count} old notification log entries")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old notification logs: {e}")
            db.session.rollback()
            return 0

    def test_notification_channel(self, channel_id: int) -> tuple[bool, str]:
        """Test a notification channel"""
        try:
            channel = NotificationChannel.query.get(channel_id)
            if not channel:
                return False, "Channel not found"

            success = channel.test_connection()

            if success:
                return True, "Test notification sent successfully"
            else:
                return False, "Failed to send test notification"

        except Exception as e:
            logger.error(f"Error testing notification channel {channel_id}: {e}")
            return False, f"Test failed: {str(e)}"


# Global notification service instance
notification_service = NotificationService()
