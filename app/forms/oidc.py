"""OIDC Provider Configuration Forms."""

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, URL, Optional, ValidationError


class ClientSecretField(StringField):
    """Custom field for client secret that supports masking."""

    def process_formdata(self, valuelist):
        """Process form data, detecting masked values."""
        if valuelist and len(valuelist) > 0:
            value = valuelist[0]
            # If the value is masked (all asterisks), don't update the secret
            if value and "*" in value and not value.strip("*"):
                # This is a masked value, skip processing
                return
        super().process_formdata(valuelist)

    def populate_obj(self, obj, name):
        """Only populate if the value is not masked."""
        value = self.data
        # If the value is masked (contains asterisks and is mostly asterisks), don't update
        if value and "*" in value and len(value.strip("*")) < len(value) / 2:
            # This is likely a masked value, don't update the object
            return
        super().populate_obj(obj, name)


class OIDCProviderForm(FlaskForm):
    """Form for creating and editing OIDC providers."""

    name = StringField(
        "Provider Name",
        validators=[DataRequired()],
        description="Internal name (e.g., 'google', 'microsoft')",
    )
    display_name = StringField(
        "Display Name",
        validators=[DataRequired()],
        description="Name shown to users (e.g., 'Google', 'Microsoft')",
    )

    # Configuration type selection
    config_type = SelectField(
        "Configuration",
        choices=[("discovery", "Auto-discovery"), ("manual", "Manual URLs")],
        default="discovery",
        description="Choose auto-discovery or manual configuration",
    )

    # Auto-discovery fields
    issuer_url = StringField(
        "Issuer URL",
        validators=[Optional(), URL()],
        description="e.g., https://accounts.google.com for auto-discovery",
    )

    # Manual configuration fields
    client_id = StringField(
        "Client ID",
        validators=[DataRequired()],
        description="OAuth 2.0 Client ID from your provider",
    )
    client_secret = ClientSecretField(
        "Client Secret",
        validators=[DataRequired()],
        description="OAuth 2.0 Client Secret from your provider",
    )

    auth_url = StringField(
        "Authorization URL",
        validators=[Optional(), URL()],
        description="OAuth 2.0 authorization endpoint (manual config only)",
    )
    token_url = StringField(
        "Token URL",
        validators=[Optional(), URL()],
        description="OAuth 2.0 token endpoint (manual config only)",
    )
    jwks_url = StringField(
        "JWKS URL",
        validators=[Optional(), URL()],
        description="JSON Web Key Set endpoint (manual config only)",
    )
    userinfo_url = StringField(
        "Userinfo URL",
        validators=[Optional(), URL()],
        description="User info endpoint (manual config only, optional)",
    )

    scope = StringField(
        "Scope",
        default="openid email profile",
        description="Requested scopes (space-separated)",
    )
    is_active = BooleanField(
        "Active", default=True, description="Enable this provider for user login"
    )
    submit = SubmitField("Save Provider")

    def validate_issuer_url(self, field):
        """Validate issuer URL based on configuration type."""
        if self.config_type.data == "discovery" and not field.data:
            raise ValidationError(
                "Issuer URL is required for auto-discovery configuration"
            )

    def validate(self, extra_validators=None):
        """Validate form based on configuration type."""
        if not super().validate(extra_validators):
            return False

        # For manual configuration, require specific URLs
        if self.config_type.data == "manual":
            required_fields = ["auth_url", "token_url", "jwks_url"]
            for field_name in required_fields:
                field = getattr(self, field_name)
                if not field.data:
                    field.errors.append(
                        "This field is required for manual configuration"
                    )
                    return False

        return True
