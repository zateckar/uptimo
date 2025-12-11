"""Public status page forms."""

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    TextAreaField,
    BooleanField,
    SubmitField,
    SelectMultipleField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    Optional,
    ValidationError,
)
from wtforms.widgets import CheckboxInput, ListWidget
from app.models.monitor import Monitor


class MultiCheckboxField(SelectMultipleField):
    """A multiple-select field that renders checkboxes."""

    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class PublicStatusPageForm(FlaskForm):
    """Form for creating and editing public status pages."""

    custom_header = StringField(
        "Custom Header",
        validators=[
            Optional(),
            Length(max=200, message="Header must be less than 200 characters"),
        ],
        description="Custom header text for the status page",
    )

    description = TextAreaField(
        "Description",
        validators=[
            Optional(),
            Length(max=1000, message="Description must be less than 1000 characters"),
        ],
        description="Description text shown on the status page",
    )

    url_type = SelectField(
        "URL Type",
        choices=[
            ("uuid", "Hidden Link (UUID + randomness)"),
            ("simple", "Simple Path (/status)"),
        ],
        validators=[DataRequired(message="URL type is required")],
        description="Choose how the status page should be accessible",
    )

    selected_monitors = MultiCheckboxField(
        "Selected Monitors",
        validators=[],
        description="Select monitors to display on the status page",
    )

    is_active = BooleanField("Active", default=True)

    submit = SubmitField("Save Status Page")

    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop("user_id", None)
        super().__init__(*args, **kwargs)
        # Always populate available monitors for the current user
        # Admin should only see their own monitors for security and clarity
        if self.user_id:
            self.selected_monitors.choices = [
                (str(monitor.id), monitor.name)
                for monitor in Monitor.query.filter_by(
                    user_id=self.user_id, is_active=True
                )
                .order_by(Monitor.name)
                .all()
            ]
        else:
            # If no user_id provided, show empty choices to prevent
            # exposing all monitors to potentially unauthorized users
            self.selected_monitors.choices = []

    def validate_selected_monitors(self, field):
        """Validate that at least one monitor is selected."""
        if not field.data:
            raise ValidationError("At least one monitor must be selected")

    def validate_url_type(self, field):
        """Validate URL type uniqueness for simple paths."""
        if field.data == "simple":
            # Check if there's already an active simple status page
            from app.models.public_status_page import PublicStatusPage

            existing = PublicStatusPage.query.filter_by(
                url_type="simple", is_active=True
            ).first()

            # If editing existing page, allow keeping the same type
            if hasattr(self, "_obj") and self._obj and self._obj.url_type == "simple":
                return

            if existing:
                raise ValidationError(
                    "A public status page with simple URL (/status) already exists. "
                    "Only one can be active at a time."
                )


class PublicStatusPageEditForm(PublicStatusPageForm):
    """Form for editing existing public status pages."""

    def __init__(self, *args, **kwargs):
        # Store the object for validation
        if "obj" in kwargs:
            self._obj = kwargs["obj"]
        super().__init__(*args, **kwargs)

    submit = SubmitField("Update Status Page")

    def process(
        self,
        formdata=None,
        obj=None,
        data=None,
        extra_filters=None,
        **kwargs,
    ):
        """Process form data."""
        super().process(formdata, obj, data, extra_filters, **kwargs)
