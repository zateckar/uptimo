import logging
import requests
from typing import Any, Optional
from flask import current_app
from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)


class TelegramNotifier(BaseNotifier):
    """Telegram notification provider using Bot API"""

    def send(
        self,
        channel: Any,
        title: str,
        message: str,
        monitor: Optional[Any] = None,
        incident: Optional[Any] = None,
    ) -> bool:
        """Send Telegram notification"""
        try:
            config = channel.get_config()
            bot_token = config.get(
                "bot_token", current_app.config.get("TELEGRAM_BOT_TOKEN")
            )
            chat_id = config.get("chat_id")

            if not bot_token:
                logger.error("Telegram bot token not configured")
                return False

            if not chat_id:
                logger.error("Telegram chat ID not configured")
                return False

            # Format message for Telegram
            formatted_message = self._format_telegram_message(
                title, message, monitor, incident
            )

            # Send message
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": formatted_message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                logger.info(f"Telegram message sent successfully to chat {chat_id}")
                return True
            else:
                logger.error(
                    f"Telegram API error: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    def _format_telegram_message(self, title, message, monitor=None, incident=None):
        """Format message for Telegram with HTML markup"""
        formatted = f"<b>{title}</b>\n\n{message}"

        if monitor:
            formatted += "\n\n<b>Monitor Details:</b>\n"
            formatted += f"<i>Name:</i> {monitor.name}\n"
            formatted += f"<i>Type:</i> {monitor.type.value.upper()}\n"
            formatted += f"<i>Target:</i> <code>{monitor.target}</code>\n"
            formatted += f"<i>Check Interval:</i> {monitor.check_interval.value}s"

        if incident:
            formatted += "\n\n<b>Incident Details:</b>\n"
            formatted += f"<i>Started:</i> {incident.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            if incident.is_active():
                duration = incident.get_duration_formatted()
                formatted += f"<i>Duration:</i> {duration}\n"
            else:
                formatted += f"<i>Resolved:</i> {incident.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                formatted += f"<i>Duration:</i> {incident.get_duration_formatted()}\n"

        # Add footer
        formatted += "\n\n— Uptimo Monitoring"

        return formatted

    def test_connection(self, channel: Any) -> bool:
        """Test Telegram connection"""
        try:
            config = channel.get_config()
            bot_token = config.get(
                "bot_token", current_app.config.get("TELEGRAM_BOT_TOKEN")
            )
            chat_id = config.get("chat_id")

            if not bot_token:
                logger.error("Bot token not configured")
                return False

            if not chat_id:
                logger.error("Chat ID not configured")
                return False

            # Test by sending a test message
            title = "🧪 Uptimo Test"
            message = "This is a test message from Uptimo to verify your Telegram notification settings."

            return self.send(channel, title, message)

        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False

    def get_bot_info(self, bot_token=None):
        """Get bot information"""
        try:
            token = bot_token or current_app.config.get("TELEGRAM_BOT_TOKEN")
            if not token:
                return None

            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                return response.json().get("result")
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            return None

    def get_chat_info(self, bot_token=None, chat_id=None):
        """Get chat information"""
        try:
            token = bot_token or current_app.config.get("TELEGRAM_BOT_TOKEN")
            if not token:
                return None

            url = f"https://api.telegram.org/bot{token}/getChat"
            data = {"chat_id": chat_id}

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                return response.json().get("result")
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to get chat info: {e}")
            return None
