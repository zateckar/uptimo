"""Application settings form."""

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class AppSettingsForm(FlaskForm):
    """Form for application-wide settings."""

    log_level = SelectField(
        "Log Level",
        choices=[
            ("DEBUG", "Debug"),
            ("INFO", "Info"),
            ("WARNING", "Warning"),
            ("ERROR", "Error"),
            ("CRITICAL", "Critical"),
        ],
        validators=[DataRequired()],
    )

    timezone = SelectField(
        "Application Timezone",
        choices=[
            ("UTC", "UTC"),
            ("Europe/Prague", "Europe/Prague"),
            ("Europe/London", "Europe/London"),
            ("Europe/Paris", "Europe/Paris"),
            ("Europe/Berlin", "Europe/Berlin"),
            ("America/New_York", "America/New York"),
            ("America/Chicago", "America/Chicago"),
            ("America/Denver", "America/Denver"),
            ("America/Los_Angeles", "America/Los Angeles"),
            ("Asia/Tokyo", "Asia/Tokyo"),
            ("Asia/Shanghai", "Asia/Shanghai"),
            ("Asia/Singapore", "Asia/Singapore"),
            ("Australia/Sydney", "Australia/Sydney"),
        ],
        validators=[DataRequired()],
    )

    data_retention_days = IntegerField(
        "Data Retention (Days)",
        validators=[
            DataRequired(),
            NumberRange(min=1, max=3650, message="Must be between 1 and 3650 days"),
        ],
        default=365,
    )

    submit = SubmitField("Save Settings")


class DeleteOldRecordsForm(FlaskForm):
    """Form for deleting old check records."""

    days = IntegerField(
        "Delete records older than (days)",
        validators=[
            DataRequired(),
            NumberRange(min=1, max=3650, message="Must be between 1 and 3650 days"),
        ],
        default=90,
    )

    submit = SubmitField("Delete Old Records")
