import logging
import requests
import time
from typing import Any, Optional
from flask import current_app
from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)


class SlackNotifier(BaseNotifier):
    """Slack notification provider using Webhooks"""

    def send(
        self,
        channel: Any,
        title: str,
        message: str,
        monitor: Optional[Any] = None,
        incident: Optional[Any] = None,
    ) -> bool:
        """Send Slack notification"""
        try:
            config = channel.get_config()
            webhook_url = config.get(
                "webhook_url", current_app.config.get("SLACK_WEBHOOK_URL")
            )

            if not webhook_url:
                logger.error("Slack webhook URL not configured")
                return False

            # Format message for Slack
            slack_message = self._format_slack_message(
                title, message, monitor, incident
            )

            # Send message
            response = requests.post(
                webhook_url,
                json=slack_message,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if response.status_code == 200:
                logger.info("Slack message sent successfully")
                return True
            else:
                logger.error(
                    f"Slack webhook error: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def _format_slack_message(self, title, message, monitor=None, incident=None):
        """Format message for Slack"""
        # Determine color based on title
        if "🔴" in title or "Down" in title:
            color = "danger"
        elif "🟢" in title or "Up" in title:
            color = "good"
        elif "⚠️" in title or "Warning" in title:
            color = "warning"
        else:
            color = "#36a64f"  # Default green

        slack_message = {
            "attachments": [
                {
                    "color": color,
                    "title": title.replace("🔴", "")
                    .replace("🟢", "")
                    .replace("⚠️", "")
                    .strip(),
                    "text": message,
                    "footer": "Uptimo Monitoring",
                    "ts": int(time.time()),
                }
            ]
        }

        # Add monitor details
        if monitor:
            monitor_fields = [
                {"title": "Monitor Name", "value": monitor.name, "short": True},
                {"title": "Type", "value": monitor.type.value.upper(), "short": True},
                {"title": "Target", "value": f"`{monitor.target}`", "short": False},
                {
                    "title": "Check Interval",
                    "value": f"{monitor.check_interval.value}s",
                    "short": True,
                },
            ]

            slack_message["attachments"][0]["fields"] = monitor_fields

        # Add incident details
        if incident:
            if "fields" in slack_message["attachments"][0]:
                incident_fields = slack_message["attachments"][0]["fields"]
                # Ensure it's a list
                if not isinstance(incident_fields, list):
                    incident_fields = []
                    slack_message["attachments"][0]["fields"] = incident_fields
            else:
                incident_fields = []
                slack_message["attachments"][0]["fields"] = incident_fields

            incident_fields.extend(
                [
                    {
                        "title": "Incident Started",
                        "value": incident.started_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "short": True,
                    }
                ]
            )

            if incident.is_active():
                duration = incident.get_duration_formatted()
                incident_fields.append(
                    {"title": "Duration", "value": duration, "short": True}
                )
            else:
                incident_fields.extend(
                    [
                        {
                            "title": "Resolved",
                            "value": incident.resolved_at.strftime(
                                "%Y-%m-%d %H:%M:%S UTC"
                            ),
                            "short": True,
                        },
                        {
                            "title": "Duration",
                            "value": incident.get_duration_formatted(),
                            "short": True,
                        },
                    ]
                )

        return slack_message

    def test_connection(self, channel: Any) -> bool:
        """Test Slack connection"""
        try:
            config = channel.get_config()
            webhook_url = config.get(
                "webhook_url", current_app.config.get("SLACK_WEBHOOK_URL")
            )

            if not webhook_url:
                logger.error("Webhook URL not configured")
                return False

            # Test by sending a test message
            title = "🧪 Uptimo Test"
            message = "This is a test message from Uptimo to verify your Slack notification settings."

            return self.send(channel, title, message)

        except Exception as e:
            logger.error(f"Slack connection test failed: {e}")
            return False

    def get_channel_info(self, webhook_url=None):
        """Get information about the Slack channel"""
        try:
            url = webhook_url or current_app.config.get("SLACK_WEBHOOK_URL")
            if not url:
                return None

            # Extract team ID from webhook URL if possible
            if "/services/" in url:
                parts = url.split("/services/")
                if len(parts) > 1:
                    service_parts = parts[1].split("/")
                    if len(service_parts) >= 2:
                        team_id = service_parts[0]
                        return {"team_id": team_id, "webhook_url": url}

            return {"webhook_url": url}

        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            return None
