import json
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    BooleanField,
    IntegerField,
    SubmitField,
    PasswordField,
    URLField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
    Email,
    URL,
)
from app.models.notification import NotificationType


class NotificationChannelForm(FlaskForm):
    """Form for creating and editing notification channels"""

    # Basic Information
    name = StringField(
        "Channel Name",
        validators=[
            DataRequired(message="Channel name is required"),
            Length(min=1, max=100, message="Name must be between 1 and 100 characters"),
        ],
    )

    type = SelectField(
        "Channel Type",
        choices=[
            (NotificationType.EMAIL.value, "Email"),
            (NotificationType.TELEGRAM.value, "Telegram"),
            (NotificationType.SLACK.value, "Slack"),
        ],
        validators=[DataRequired(message="Channel type is required")],
    )

    is_active = BooleanField("Active Channel", default=True)

    # Email Configuration
    smtp_server = StringField(
        "SMTP Server",
        validators=[Optional(), Length(max=255)],
        description="SMTP server hostname (e.g., smtp.gmail.com)",
    )
    smtp_port = IntegerField(
        "SMTP Port",
        validators=[Optional(), NumberRange(min=1, max=65535)],
        default=587,
        description="SMTP server port (usually 587 for TLS, 465 for SSL)",
    )
    use_tls = BooleanField("Use TLS", default=True, description="Use TLS encryption")
    smtp_username = StringField(
        "SMTP Username",
        validators=[Optional(), Length(max=255)],
        description="SMTP username (often your email)",
    )
    smtp_password = PasswordField(
        "SMTP Password",
        validators=[Optional()],
        description="SMTP password or app password",
    )
    from_email = StringField(
        "From Email",
        validators=[
            Optional(),
            Email(message="Please enter a valid email address"),
            Length(max=255),
        ],
        description="Sender email address",
    )
    to_email = StringField(
        "Recipient Email",
        validators=[
            Optional(),
            Email(message="Please enter a valid email address"),
            Length(max=255),
        ],
        description="Recipient email address",
    )

    # Telegram Configuration
    bot_token = StringField(
        "Bot Token",
        validators=[Optional(), Length(max=255)],
        description="Telegram bot token from @BotFather",
    )
    chat_id = StringField(
        "Chat ID",
        validators=[Optional(), Length(max=50)],
        description="Telegram chat ID (user or group)",
    )

    # Slack Configuration
    webhook_url = URLField(
        "Webhook URL",
        validators=[Optional(), URL(message="Please enter a valid URL")],
        description="Slack incoming webhook URL",
    )
    channel = StringField(
        "Slack Channel",
        validators=[Optional(), Length(max=50)],
        description="Slack channel name (e.g., #alerts)",
    )
    username = StringField(
        "Bot Username",
        validators=[Optional(), Length(max=50)],
        default="Uptimo",
        description="Bot username for Slack messages",
    )

    submit = SubmitField("Create Channel")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_type = None

    def validate_name(self, name):
        """Validate channel name uniqueness for the user"""
        from app.models.notification import NotificationChannel

        if not hasattr(self, "obj") or not self.obj:
            # Creating new channel
            existing = NotificationChannel.query.filter_by(
                user_id=self.user_id, name=name.data
            ).first()
            if existing:
                raise ValidationError("A channel with this name already exists")
        else:
            # Editing existing channel
            existing = NotificationChannel.query.filter(
                NotificationChannel.user_id == self.user_id,
                NotificationChannel.name == name.data,
                NotificationChannel.id != self.obj.id,
            ).first()
            if existing:
                raise ValidationError("A channel with this name already exists")

    def validate_to_email(self, to_email):
        """Validate recipient email is provided for email channels"""
        if self.type.data == NotificationType.EMAIL.value and not to_email.data:
            raise ValidationError("Recipient email is required for email channels")

    def validate_bot_token(self, bot_token):
        """Validate bot token is provided for Telegram channels"""
        if self.type.data == NotificationType.TELEGRAM.value and not bot_token.data:
            raise ValidationError("Bot token is required for Telegram channels")

    def validate_chat_id(self, chat_id):
        """Validate chat ID is provided for Telegram channels"""
        if self.type.data == NotificationType.TELEGRAM.value and not chat_id.data:
            raise ValidationError("Chat ID is required for Telegram channels")

    def validate_webhook_url(self, webhook_url):
        """Validate webhook URL is provided for Slack channels"""
        if self.type.data == NotificationType.SLACK.value and not webhook_url.data:
            raise ValidationError("Webhook URL is required for Slack channels")

    def get_config(self):
        """Get configuration as JSON string"""
        config = {}

        if self.type.data == NotificationType.EMAIL.value:
            # Get existing config to preserve password if not changed
            existing_config = {}
            if hasattr(self, "obj") and self.obj:
                existing_config = self.obj.get_config()

            config.update(
                {
                    "smtp_server": self.smtp_server.data,
                    "smtp_port": self.smtp_port.data,
                    "use_tls": self.use_tls.data,
                    "username": self.smtp_username.data,
                    "password": self.smtp_password.data
                    or existing_config.get("password"),
                    "from_email": self.from_email.data,
                    "to_email": self.to_email.data,
                }
            )
        elif self.type.data == NotificationType.TELEGRAM.value:
            config.update(
                {
                    "bot_token": self.bot_token.data,
                    "chat_id": self.chat_id.data,
                }
            )
        elif self.type.data == NotificationType.SLACK.value:
            config.update(
                {
                    "webhook_url": self.webhook_url.data,
                    "channel": self.channel.data or "#alerts",
                    "username": self.username.data or "Uptimo",
                }
            )

        return json.dumps(config)

    def set_config(self, config_str):
        """Set form fields from configuration JSON string"""
        if not config_str:
            return

        try:
            config = json.loads(config_str)
        except (json.JSONDecodeError, TypeError):
            return

        if self.type.data == NotificationType.EMAIL.value:
            self.smtp_server.data = config.get("smtp_server")
            self.smtp_port.data = config.get("smtp_port", 587)
            self.use_tls.data = config.get("use_tls", True)
            self.smtp_username.data = config.get("username")
            self.from_email.data = config.get("from_email")
            self.to_email.data = config.get("to_email")
            # Don't set password from config for security
        elif self.type.data == NotificationType.TELEGRAM.value:
            self.bot_token.data = config.get("bot_token")
            self.chat_id.data = config.get("chat_id")
        elif self.type.data == NotificationType.SLACK.value:
            self.webhook_url.data = config.get("webhook_url")
            self.channel.data = config.get("channel", "#alerts")
            self.username.data = config.get("username", "Uptimo")


class NotificationChannelEditForm(NotificationChannelForm):
    """Form for editing existing notification channels"""

    submit = SubmitField("Update Channel")


class MonitorNotificationForm(FlaskForm):
    """Form for configuring monitor notification settings"""

    channel_id = SelectField(
        "Notification Channel",
        coerce=int,
        validators=[DataRequired(message="Please select a notification channel")],
    )

    is_enabled = BooleanField("Enable Notifications", default=True)
    notify_on_down = BooleanField("Notify when monitor goes down", default=True)
    notify_on_up = BooleanField("Notify when monitor comes back up", default=True)
    notify_on_ssl_warning = BooleanField("Notify on SSL warnings", default=True)

    consecutive_checks_threshold = IntegerField(
        "Consecutive failures before alert",
        validators=[
            Optional(),
            NumberRange(
                min=1,
                max=10,
                message="Threshold must be between 1 and 10 checks",
            ),
        ],
        default=1,
        description=(
            "Number of consecutive DOWN checks before sending notification "
            "(prevents false alerts)"
        ),
    )

    escalate_after_minutes = IntegerField(
        "Escalate after (minutes)",
        validators=[
            Optional(),
            NumberRange(
                min=1,
                max=10080,
                message="Escalation time must be between 1 and 10080 minutes",
            ),
        ],
        description="Send additional notification after X minutes of downtime",
    )

    submit = SubmitField("Save Notification Settings")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set channel choices
        if hasattr(self, "user_id") and self.user_id:
            from app.models.notification import NotificationChannel

            channels = NotificationChannel.query.filter_by(
                user_id=self.user_id, is_active=True
            ).all()

            self.channel_id.choices = [
                (channel.id, f"{channel.name} ({channel.type.value})")
                for channel in channels
            ]


class TestNotificationForm(FlaskForm):
    """Form for testing notification channels"""

    submit = SubmitField("Send Test Notification")
