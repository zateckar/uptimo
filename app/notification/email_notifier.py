import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Email notification provider using SMTP or SendGrid"""

    def send(self, channel, title, message, monitor=None, incident=None):
        """Send email notification"""
        try:
            config = channel.get_config()

            # Format message
            formatted_message = self.format_message(title, message, monitor, incident)

            # Check if using SendGrid
            if current_app.config.get("SENDGRID_API_KEY"):
                return self._send_sendgrid(config, title, formatted_message)
            else:
                return self._send_smtp(config, title, formatted_message)

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    def _send_smtp(self, config, title, message):
        """Send email using SMTP"""
        try:
            # Get SMTP configuration
            smtp_server = config.get(
                "smtp_server", current_app.config.get("MAIL_SERVER")
            )
            smtp_port = config.get(
                "smtp_port", current_app.config.get("MAIL_PORT", 587)
            )
            use_tls = config.get(
                "use_tls", current_app.config.get("MAIL_USE_TLS", True)
            )
            username = config.get("username", current_app.config.get("MAIL_USERNAME"))
            password = config.get("password", current_app.config.get("MAIL_PASSWORD"))
            from_email = config.get(
                "from_email", current_app.config.get("MAIL_DEFAULT_SENDER")
            )
            to_email = config.get("to_email")

            if not to_email:
                logger.error("No recipient email configured")
                return False

            # Create message
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = to_email
            msg["Subject"] = title

            # Add body
            msg.attach(MIMEText(message, "plain"))

            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls()

                if username and password:
                    server.login(username, password)

                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMTP email: {e}")
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

            # Create email
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
                    f"SendGrid email failed with status {response.status_code}"
                )
                return False

        except ImportError:
            logger.error("SendGrid library not installed")
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
