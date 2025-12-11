import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.models.monitor import Monitor
from app.models.incident import Incident
from app.services.checker import CheckerFactory
from app.services.public_status_service import PublicStatusService
from app.notification.service import NotificationService

# Global scheduler instance
scheduler = BackgroundScheduler()

logger = logging.getLogger(__name__)


class MonitorScheduler:
    """Service for scheduling and executing monitor checks"""

    def __init__(self):
        self.notification_service = NotificationService()
        self._setup_scheduler_handlers()

    def _setup_scheduler_handlers(self):
        """Setup scheduler event handlers"""
        scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)

    def _job_executed(self, event: Any) -> None:
        """Handle successful job execution"""
        logger.debug(f"Job {event.job_id} executed successfully")

    def _job_error(self, event: Any) -> None:
        """Handle job execution errors"""
        logger.error(f"Job {event.job_id} failed: {event.exception}")

    def schedule_all_monitors(self, run_immediately: bool = True):
        """Schedule all active monitors

        Args:
            run_immediately: If True, run first check immediately for all monitors
        """
        monitors = Monitor.query.filter_by(is_active=True).all()

        for monitor in monitors:
            self.schedule_monitor(monitor, run_immediately=run_immediately)

        logger.info(f"Scheduled {len(monitors)} active monitors")

    def schedule_monitor(self, monitor: Any, run_immediately: bool = False) -> None:
        """Schedule a single monitor

        Args:
            monitor: Monitor instance to schedule
            run_immediately: If True, run the first check immediately
        """
        job_id = f"monitor_{monitor.id}"

        # Remove existing job if it exists
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass

        # Add new job
        try:
            scheduler.add_job(
                func=self._execute_monitor_check,
                trigger=IntervalTrigger(seconds=monitor.check_interval.value),
                args=[monitor.id],
                id=job_id,
                name=f"Monitor check for {monitor.name}",
                replace_existing=True,
                max_instances=1,  # Prevent overlapping checks
                coalesce=True,  # Combine missed executions
            )
            logger.info(
                f"Scheduled monitor {monitor.name} (ID: {monitor.id}) "
                f"with interval {monitor.check_interval.value}s"
            )

            # Run immediate check if requested or if monitor has never been checked
            if run_immediately or monitor.last_check is None:
                logger.info(
                    f"Running immediate check for monitor {monitor.name} (ID: {monitor.id})"
                )
                scheduler.add_job(
                    func=self._execute_monitor_check,
                    args=[monitor.id],
                    id=f"monitor_{monitor.id}_immediate",
                    replace_existing=True,
                )
        except Exception as e:
            logger.error(f"Failed to schedule monitor {monitor.name}: {e}")

    def unschedule_monitor(self, monitor_id: int) -> None:
        """Unschedule a monitor"""
        job_id = f"monitor_{monitor_id}"

        try:
            scheduler.remove_job(job_id)
            logger.info(f"Unscheduled monitor (ID: {monitor_id})")
        except Exception:
            pass

    def _execute_monitor_check(self, monitor_id: int) -> None:
        """Execute a single monitor check"""
        # Import app here to avoid circular imports
        from app import create_app

        # CRITICAL: start_scheduler=False to avoid re-initializing scheduler
        app = create_app(start_scheduler=False)
        with app.app_context():  # Ensure we have Flask app context
            try:
                # Get fresh monitor data from database
                monitor = Monitor.query.get(monitor_id)
                if not monitor or not monitor.is_active:
                    logger.info(
                        f"Monitor {monitor_id} not found or inactive, skipping check"
                    )
                    return

                logger.debug(
                    f"Executing check for monitor {monitor.name} (ID: {monitor_id})"
                )

                # Create checker and perform check
                checker = CheckerFactory.create_checker(monitor)
                check_result = checker.check()

                # Get previous status to detect changes
                previous_status = monitor.last_status

                # Update monitor status
                monitor.update_status(
                    status=check_result.status,
                    response_time=check_result.response_time,
                    status_code=check_result.status_code,
                    error_message=check_result.error_message,
                    additional_data=check_result.additional_data,
                )

                # Invalidate cache when monitor status changes
                if previous_status != check_result.status:
                    PublicStatusService.invalidate_monitor_cache(monitor.id)

                # Send notifications if status changed
                if previous_status != check_result.status:
                    self._handle_status_change(monitor, previous_status, check_result)

                # Check for SSL warnings
                if (
                    check_result.additional_data
                    and "cert_info" in check_result.additional_data
                ):
                    cert_info = check_result.additional_data["cert_info"]
                    days_to_expiration = cert_info.get("days_to_expiration", 999)

                    if days_to_expiration <= monitor.cert_expiration_threshold:
                        self._handle_ssl_warning(monitor, cert_info)

                logger.debug(
                    f"Check completed for monitor {monitor.name}: {check_result.status}"
                )

            except Exception as e:
                logger.error(f"Error executing check for monitor {monitor_id}: {e}")

                # Try to update monitor with error status
                try:
                    monitor = Monitor.query.get(monitor_id)
                    if monitor:
                        monitor.update_status(
                            status="down",
                            error_message=f"Check execution error: {str(e)}",
                            additional_data=None,
                        )
                except Exception:
                    pass

    def _handle_status_change(
        self, monitor: Any, previous_status: str, check_result: Any
    ) -> None:
        """Handle status change notifications"""
        try:
            if check_result.status == "down" and previous_status != "down":
                # Monitor went down
                title = f"🔴 Monitor Down: {monitor.name}"
                message = f"Your monitor '{monitor.name}' ({monitor.type.value.upper()}: {monitor.target}) is now down."

                if check_result.error_message:
                    message += f"\n\nError: {check_result.error_message}"

                if check_result.response_time:
                    message += f"\n\nResponse time: {check_result.response_time:.2f}ms"

                # Get active incident
                incident = monitor.get_active_incident()

                self.notification_service.send_monitor_notification(
                    monitor=monitor,
                    event_type="down",
                    title=title,
                    message=message,
                    incident=incident,
                )

            elif check_result.status == "up" and previous_status != "up":
                # Monitor came back up
                title = f"🟢 Monitor Up: {monitor.name}"
                message = f"Your monitor '{monitor.name}' ({monitor.type.value.upper()}: {monitor.target}) is back up."

                if check_result.response_time:
                    message += f"\n\nResponse time: {check_result.response_time:.2f}ms"

                # Get resolved incident
                incident = None
                if previous_status == "down":
                    # Look for recently resolved incident
                    recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
                    incident = monitor.incidents.filter(
                        Incident.resolved_at >= recent_time
                    ).first()

                self.notification_service.send_monitor_notification(
                    monitor=monitor,
                    event_type="up",
                    title=title,
                    message=message,
                    incident=incident,
                )

        except Exception as e:
            logger.error(f"Error handling status change for monitor {monitor.id}: {e}")

    def _handle_ssl_warning(self, monitor: Any, ssl_info: Dict[str, Any]) -> None:
        """Handle SSL certificate expiration warnings"""
        try:
            days_to_expiration = ssl_info.get("days_to_expiration", 999)

            title = f"⚠️ SSL Certificate Expiring Soon: {monitor.name}"
            message = f"SSL certificate for {monitor.target} expires in {days_to_expiration} days."

            if "subject" in ssl_info and ssl_info["subject"]:
                subjects = ", ".join(
                    [item[0][1] for item in ssl_info["subject"] if item[0][0] == "CN"]
                )
                if subjects:
                    message += f"\n\nCertificate subject: {subjects}"

            self.notification_service.send_monitor_notification(
                monitor=monitor, event_type="ssl_warning", title=title, message=message
            )

        except Exception as e:
            logger.error(f"Error handling SSL warning for monitor {monitor.id}: {e}")

    def get_scheduled_jobs(self) -> list[Dict[str, Any]]:
        """Get information about all scheduled jobs"""
        jobs = []

        for job in scheduler.get_jobs():
            if job.id.startswith("monitor_"):
                monitor_id = int(job.id.split("_")[1])
                monitor = Monitor.query.get(monitor_id)

                jobs.append(
                    {
                        "id": job.id,
                        "name": job.name,
                        "monitor_name": monitor.name if monitor else "Unknown",
                        "monitor_id": monitor_id,
                        "next_run_time": job.next_run_time.isoformat()
                        if job.next_run_time
                        else None,
                        "trigger": str(job.trigger),
                    }
                )

        return jobs

    def run_check_now(self, monitor_id: int) -> bool:
        """Run a check immediately (synchronously)"""
        from flask import current_app

        with current_app.app_context():
            try:
                monitor = Monitor.query.get(monitor_id)
                if not monitor:
                    raise ValueError(f"Monitor {monitor_id} not found")

                self._execute_monitor_check(monitor_id)
                return True

            except Exception as e:
                logger.error(
                    f"Error running immediate check for monitor {monitor_id}: {e}"
                )
                return False


# Global scheduler instance
monitor_scheduler = MonitorScheduler()


def init_scheduler() -> None:
    """Initialize the monitor scheduler"""
    try:
        # Schedule all active monitors
        monitor_scheduler.schedule_all_monitors()
        logger.info("Monitor scheduler initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize monitor scheduler: {e}")
