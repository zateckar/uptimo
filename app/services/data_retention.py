"""Data retention service for cleaning up old monitoring data."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple, Optional

from app import db
from app.models.check_result import CheckResult
from app.models.incident import Incident
from app.models.notification import NotificationLog

logger = logging.getLogger(__name__)


class DataRetentionService:
    """Service for managing data retention and cleanup."""

    def __init__(self, default_retention_days: int = 365):
        self.default_retention_days = default_retention_days
        self.retention_policies = {
            "check_results": default_retention_days,
            "incidents": default_retention_days * 2,  # Keep incidents longer
            "notification_logs": 90,  # Keep notification logs for 90 days
        }

    def set_retention_policy(self, data_type: str, days: int) -> None:
        """Set retention policy for a specific data type."""
        if days < 1:
            raise ValueError("Retention days must be at least 1")

        self.retention_policies[data_type] = days
        logger.info(f"Updated retention policy for {data_type}: {days} days")

    def get_retention_policy(self, data_type: str) -> int:
        """Get retention policy for a specific data type."""
        return self.retention_policies.get(data_type, self.default_retention_days)

    def cleanup_old_check_results(
        self, days_to_keep: Optional[int] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Clean up old check results.

        Args:
            days_to_keep: Number of days to keep data (uses default if None)

        Returns:
            Tuple of (deleted_count, cleanup_info)
        """
        if days_to_keep is None:
            days_to_keep = self.get_retention_policy("check_results")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        try:
            # Get count before deletion for reporting
            total_before = CheckResult.query.count()
            old_count = CheckResult.query.filter(
                CheckResult.timestamp < cutoff_date
            ).count()

            if old_count == 0:
                logger.info(
                    f"No check results older than {days_to_keep} days to clean up"
                )
                return 0, {
                    "deleted_count": 0,
                    "cutoff_date": cutoff_date.isoformat(),
                    "total_before": total_before,
                    "total_after": total_before,
                }

            # Delete old check results
            deleted_count = CheckResult.query.filter(
                CheckResult.timestamp < cutoff_date
            ).delete()

            db.session.commit()

            total_after = total_before - deleted_count

            cleanup_info = {
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "total_before": total_before,
                "total_after": total_after,
                "retention_days": days_to_keep,
            }

            logger.info(
                f"Cleaned up {deleted_count} old check results (older than {days_to_keep} days)"
            )

            return deleted_count, cleanup_info

        except Exception as e:
            logger.error(f"Failed to cleanup old check results: {e}")
            db.session.rollback()
            raise

    def cleanup_old_incidents(
        self, days_to_keep: Optional[int] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Clean up old resolved incidents.

        Args:
            days_to_keep: Number of days to keep data (uses default if None)

        Returns:
            Tuple of (deleted_count, cleanup_info)
        """
        if days_to_keep is None:
            days_to_keep = self.get_retention_policy("incidents")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        try:
            # Get count before deletion for reporting
            total_before = Incident.query.count()

            # Only clean up resolved incidents older than cutoff
            old_incidents_query = Incident.query.filter(
                Incident.resolved_at.isnot(None), Incident.resolved_at < cutoff_date
            )

            old_count = old_incidents_query.count()

            if old_count == 0:
                logger.info(
                    f"No resolved incidents older than {days_to_keep} days to clean up"
                )
                return 0, {
                    "deleted_count": 0,
                    "cutoff_date": cutoff_date.isoformat(),
                    "total_before": total_before,
                    "total_after": total_before,
                }

            # Delete old resolved incidents
            deleted_count = old_incidents_query.delete()

            db.session.commit()

            total_after = total_before - deleted_count

            cleanup_info = {
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "total_before": total_before,
                "total_after": total_after,
                "retention_days": days_to_keep,
                "note": "Only resolved incidents were cleaned up",
            }

            logger.info(
                f"Cleaned up {deleted_count} old resolved incidents (older than {days_to_keep} days)"
            )

            return deleted_count, cleanup_info

        except Exception as e:
            logger.error(f"Failed to cleanup old incidents: {e}")
            db.session.rollback()
            raise

    def cleanup_old_notification_logs(
        self, days_to_keep: Optional[int] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Clean up old notification logs.

        Args:
            days_to_keep: Number of days to keep data (uses default if None)

        Returns:
            Tuple of (deleted_count, cleanup_info)
        """
        if days_to_keep is None:
            days_to_keep = self.get_retention_policy("notification_logs")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        try:
            # Get count before deletion for reporting
            total_before = NotificationLog.query.count()
            old_count = NotificationLog.query.filter(
                NotificationLog.sent_at < cutoff_date
            ).count()

            if old_count == 0:
                logger.info(
                    f"No notification logs older than {days_to_keep} days to clean up"
                )
                return 0, {
                    "deleted_count": 0,
                    "cutoff_date": cutoff_date.isoformat(),
                    "total_before": total_before,
                    "total_after": total_before,
                }

            # Delete old notification logs
            deleted_count = NotificationLog.query.filter(
                NotificationLog.sent_at < cutoff_date
            ).delete()

            db.session.commit()

            total_after = total_before - deleted_count

            cleanup_info = {
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "total_before": total_before,
                "total_after": total_after,
                "retention_days": days_to_keep,
            }

            logger.info(
                f"Cleaned up {deleted_count} old notification logs (older than {days_to_keep} days)"
            )

            return deleted_count, cleanup_info

        except Exception as e:
            logger.error(f"Failed to cleanup old notification logs: {e}")
            db.session.rollback()
            raise

    def cleanup_all_old_data(self) -> Dict[str, Any]:
        """
        Clean up all old data according to retention policies.

        Returns:
            Dictionary with cleanup statistics for each data type
        """
        cleanup_summary: Dict[str, Any] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "results": {},
            "total_deleted": 0,
        }

        try:
            # Clean up check results
            deleted_results, results_info = self.cleanup_old_check_results()
            results_dict: Dict[str, Any] = cleanup_summary["results"]  # type: ignore
            results_dict["check_results"] = results_info
            total_deleted: int = cleanup_summary["total_deleted"]  # type: ignore
            cleanup_summary["total_deleted"] = total_deleted + deleted_results

            # Clean up incidents
            deleted_incidents, incidents_info = self.cleanup_old_incidents()
            results_dict["incidents"] = incidents_info
            total_deleted = cleanup_summary["total_deleted"]  # type: ignore
            cleanup_summary["total_deleted"] = total_deleted + deleted_incidents

            # Clean up notification logs
            deleted_logs, logs_info = self.cleanup_old_notification_logs()
            results_dict["notification_logs"] = logs_info
            total_deleted = cleanup_summary["total_deleted"]  # type: ignore
            cleanup_summary["total_deleted"] = total_deleted + deleted_logs

            cleanup_summary["completed_at"] = datetime.now(timezone.utc).isoformat()
            cleanup_summary["success"] = True

            logger.info(
                f"Data cleanup completed. Total records deleted: {cleanup_summary['total_deleted']}"
            )

            return cleanup_summary

        except Exception as e:
            cleanup_summary["completed_at"] = datetime.now(timezone.utc).isoformat()
            cleanup_summary["success"] = False
            cleanup_summary["error"] = str(e)

            logger.error(f"Data cleanup failed: {e}")
            raise

    def get_database_stats(self) -> Dict[str, Any]:
        """Get current database statistics for monitoring."""
        try:
            # Get oldest check result
            oldest_check = CheckResult.query.order_by(
                CheckResult.timestamp.asc()
            ).first()
            oldest_check_record = (
                oldest_check.timestamp.isoformat() if oldest_check else None
            )

            # Get newest check result
            newest_check = CheckResult.query.order_by(
                CheckResult.timestamp.desc()
            ).first()
            newest_check_record = (
                newest_check.timestamp.isoformat() if newest_check else None
            )

            # Get oldest incident
            oldest_incident = Incident.query.order_by(Incident.started_at.asc()).first()
            oldest_incident_record = (
                oldest_incident.started_at.isoformat() if oldest_incident else None
            )

            # Get newest incident
            newest_incident = Incident.query.order_by(
                Incident.started_at.desc()
            ).first()
            newest_incident_record = (
                newest_incident.started_at.isoformat() if newest_incident else None
            )

            # Get oldest notification log
            oldest_log = NotificationLog.query.order_by(
                NotificationLog.sent_at.asc()
            ).first()
            oldest_log_record = oldest_log.sent_at.isoformat() if oldest_log else None

            # Get newest notification log
            newest_log = NotificationLog.query.order_by(
                NotificationLog.sent_at.desc()
            ).first()
            newest_log_record = newest_log.sent_at.isoformat() if newest_log else None

            stats = {
                "check_results": {
                    "total_count": CheckResult.query.count(),
                    "oldest_record": oldest_check_record,
                    "newest_record": newest_check_record,
                },
                "incidents": {
                    "total_count": Incident.query.count(),
                    "active_count": Incident.query.filter(
                        Incident.resolved_at.is_(None)
                    ).count(),
                    "oldest_record": oldest_incident_record,
                    "newest_record": newest_incident_record,
                },
                "notification_logs": {
                    "total_count": NotificationLog.query.count(),
                    "oldest_record": oldest_log_record,
                    "newest_record": newest_log_record,
                },
                "retention_policies": self.retention_policies.copy(),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise

    def estimate_cleanup_impact(self) -> Dict[str, Any]:
        """Estimate the impact of running cleanup without actually deleting data."""
        estimate: Dict[str, Any] = {
            "estimated_deletions": {},
            "total_estimated_deletions": 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Estimate check results to delete
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=self.get_retention_policy("check_results")
            )
            check_results_to_delete = CheckResult.query.filter(
                CheckResult.timestamp < cutoff_date
            ).count()
            deletions_dict: Dict[str, Any] = estimate["estimated_deletions"]  # type: ignore
            deletions_dict["check_results"] = {
                "count": check_results_to_delete,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": self.get_retention_policy("check_results"),
            }
            total_est: int = estimate["total_estimated_deletions"]  # type: ignore
            estimate["total_estimated_deletions"] = total_est + check_results_to_delete

            # Estimate incidents to delete
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=self.get_retention_policy("incidents")
            )
            incidents_to_delete = Incident.query.filter(
                Incident.resolved_at.isnot(None), Incident.resolved_at < cutoff_date
            ).count()
            deletions_dict["incidents"] = {
                "count": incidents_to_delete,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": self.get_retention_policy("incidents"),
            }
            total_est = estimate["total_estimated_deletions"]  # type: ignore
            estimate["total_estimated_deletions"] = total_est + incidents_to_delete

            # Estimate notification logs to delete
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=self.get_retention_policy("notification_logs")
            )
            notification_logs_to_delete = NotificationLog.query.filter(
                NotificationLog.sent_at < cutoff_date
            ).count()
            deletions_dict["notification_logs"] = {
                "count": notification_logs_to_delete,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": self.get_retention_policy("notification_logs"),
            }
            total_est = estimate["total_estimated_deletions"]  # type: ignore
            estimate["total_estimated_deletions"] = (
                total_est + notification_logs_to_delete
            )

            return estimate

        except Exception as e:
            logger.error(f"Failed to estimate cleanup impact: {e}")
            raise


# Global data retention service instance
data_retention_service = DataRetentionService()
