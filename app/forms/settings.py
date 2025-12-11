"""Application settings form."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp


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

    # Color customization fields
    enable_custom_colors = BooleanField("Enable Custom Colors")

    # Brand colors
    primary_color = StringField(
        "Primary Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #59bc87)",
            ),
        ],
        description="Main brand color for buttons, links, and primary elements",
    )

    primary_hover_color = StringField(
        "Primary Hover Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #45a676)",
            ),
        ],
        description="Color for primary elements on hover",
    )

    primary_subtle_color = StringField(
        "Primary Subtle Color",
        validators=[Optional(), Length(max=50, message="Too long")],
        description="Background color for primary elements (rgba format)",
    )

    # Status colors
    success_color = StringField(
        "Success Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #22c55e)",
            ),
        ],
        description="Color for success states and positive indicators",
    )

    success_bg_color = StringField(
        "Success Background Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #f0fdf4)",
            ),
        ],
        description="Background color for success elements",
    )

    danger_color = StringField(
        "Danger Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #dc2626)",
            ),
        ],
        description="Color for danger states and negative indicators",
    )

    danger_bg_color = StringField(
        "Danger Background Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #fef2f2)",
            ),
        ],
        description="Background color for danger elements",
    )

    warning_color = StringField(
        "Warning Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #f59e0b)",
            ),
        ],
        description="Color for warning states",
    )

    warning_bg_color = StringField(
        "Warning Background Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #fffbeb)",
            ),
        ],
        description="Background color for warning elements",
    )

    info_color = StringField(
        "Info Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #06b6d4)",
            ),
        ],
        description="Color for informational states",
    )

    info_bg_color = StringField(
        "Info Background Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #ecfeff)",
            ),
        ],
        description="Background color for info elements",
    )

    unknown_color = StringField(
        "Unknown Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #6b7280)",
            ),
        ],
        description="Color for unknown states",
    )

    unknown_bg_color = StringField(
        "Unknown Background Color",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #f3f4f6)",
            ),
        ],
        description="Background color for unknown elements",
    )

    # Dark mode overrides (optional)
    dark_primary_color = StringField(
        "Dark Mode Primary Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #3b82f6)",
            ),
        ],
        description="Override primary color for dark theme",
    )

    dark_primary_hover_color = StringField(
        "Dark Mode Primary Hover Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #60a5fa)",
            ),
        ],
        description="Override primary hover color for dark theme",
    )

    dark_primary_subtle_color = StringField(
        "Dark Mode Primary Subtle Color (Optional)",
        validators=[Optional(), Length(max=50, message="Too long")],
        description="Override primary subtle background for dark theme (rgba format)",
    )

    # Dark mode status colors
    dark_success_color = StringField(
        "Dark Mode Success Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #4ade80)",
            ),
        ],
        description="Override success color for dark theme",
    )

    dark_success_bg_color = StringField(
        "Dark Mode Success Background Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #052e16)",
            ),
        ],
        description="Override success background for dark theme",
    )

    dark_danger_color = StringField(
        "Dark Mode Danger Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #f87171)",
            ),
        ],
        description="Override danger color for dark theme",
    )

    dark_danger_bg_color = StringField(
        "Dark Mode Danger Background Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #1f0713)",
            ),
        ],
        description="Override danger background for dark theme",
    )

    dark_warning_color = StringField(
        "Dark Mode Warning Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #fbbf24)",
            ),
        ],
        description="Override warning color for dark theme",
    )

    dark_warning_bg_color = StringField(
        "Dark Mode Warning Background Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #1c1305)",
            ),
        ],
        description="Override warning background for dark theme",
    )

    dark_info_color = StringField(
        "Dark Mode Info Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #38bdf8)",
            ),
        ],
        description="Override info color for dark theme",
    )

    dark_info_bg_color = StringField(
        "Dark Mode Info Background Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #071926)",
            ),
        ],
        description="Override info background for dark theme",
    )

    dark_unknown_color = StringField(
        "Dark Mode Unknown Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #9ca3af)",
            ),
        ],
        description="Override unknown color for dark theme",
    )

    dark_unknown_bg_color = StringField(
        "Dark Mode Unknown Background Color (Optional)",
        validators=[
            Optional(),
            Regexp(
                r"^#[0-9A-Fa-f]{6}$",
                message="Must be a valid hex color (e.g., #1f2937)",
            ),
        ],
        description="Override unknown background for dark theme",
    )

    reset_colors = SubmitField("Reset to Default Colors")


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
