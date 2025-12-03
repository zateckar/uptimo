import logging
from flask import current_app
from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Email notification provider using SendGrid"""

    def send(self, channel, title, message, monitor=None, incident=None):
        """Send email notification using SendGrid"""
        try:
            config = channel.get_config()

            # Format message
            formatted_message = self.format_message(title, message, monitor, incident)

            return self._send_sendgrid(config, title, formatted_message)

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    def _send_sendgrid(self, config, title, message):
        """Send email using SendGrid"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail

            api_key = current_app.config.get("SENDGRID_API_KEY")
            if not api_key:
                logger.error("SendGrid API key not configured")
                return False

            to_email = config.get("to_email")
            from_email = config.get(
                "from_email", current_app.config.get("MAIL_DEFAULT_SENDER")
            )

            if not to_email:
                logger.error("No recipient email configured")
                return False

            # Create email with HTML formatting
            email = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=title,
                html_content=f"<pre>{message}</pre>",
            )

            # Send email
            sg = SendGridAPIClient(api_key)
            response = sg.send(email)

            if response.status_code == 202:
                logger.info(f"SendGrid email sent successfully to {to_email}")
                return True
            else:
                logger.error(
                    f"SendGrid email failed with status {response.status_code}: {response.body}"
                )
                return False

        except ImportError:
            logger.error(
                "SendGrid library not installed. Install with: uv add sendgrid"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to send SendGrid email: {e}")
            return False

    def test_connection(self, channel):
        """Test email connection"""
        try:
            title = "Uptimo Email Test"
            message = "This is a test email from Uptimo to verify your email notification settings."

            return self.send(channel, title, message)

        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False
