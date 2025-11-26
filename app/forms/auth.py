import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models.user import User


class LoginForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=80)]
    )
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Sign In")


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters long"),
        ],
    )
    new_password2 = PasswordField(
        "Repeat New Password",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords must match"),
        ],
    )
    submit = SubmitField("Change Password")

    def validate_new_password(self, new_password):
        # Password strength validation (same as registration)
        pwd = new_password.data
        if len(pwd) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        if not re.search(r"[A-Z]", pwd):
            raise ValidationError(
                "Password must contain at least one uppercase letter."
            )

        if not re.search(r"[a-z]", pwd):
            raise ValidationError(
                "Password must contain at least one lowercase letter."
            )

        if not re.search(r"\d", pwd):
            raise ValidationError("Password must contain at least one digit.")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', pwd):
            raise ValidationError(
                "Password must contain at least one special character."
            )


class UserCreateForm(FlaskForm):
    """Form for admins to create new users."""

    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=80),
        ],
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters long"),
        ],
    )
    is_admin = BooleanField("Admin User")
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Create User")

    def validate_username(self, username):
        """Validate username format and uniqueness."""
        if not re.match(r"^[a-zA-Z0-9_-]+$", username.data):
            raise ValidationError(
                "Username can only contain letters, numbers, underscores, and hyphens."
            )

        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError(
                "Username already exists. Please choose a different one."
            )

    def validate_email(self, email):
        """Validate email uniqueness."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError(
                "Email already registered. Please use a different email."
            )


class UserEditForm(FlaskForm):
    """Form for admins to edit existing users."""

    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=80),
        ],
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    is_admin = BooleanField("Admin User")
    is_active = BooleanField("Active")
    submit = SubmitField("Update User")

    def __init__(self, original_username: str, original_email: str, *args, **kwargs):
        """Initialize form with original user data for validation."""
        super().__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        """Validate username format and uniqueness (if changed)."""
        if username.data != self.original_username:
            if not re.match(r"^[a-zA-Z0-9_-]+$", username.data):
                raise ValidationError(
                    (
                        "Username can only contain letters, numbers, "
                        "underscores, and hyphens."
                    )
                )

            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError(
                    "Username already exists. Please choose a different one."
                )

    def validate_email(self, email):
        """Validate email uniqueness (if changed)."""
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError(
                    "Email already registered. Please use a different email."
                )


class AdminPasswordResetForm(FlaskForm):
    """Form for admins to reset user passwords."""

    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters long"),
        ],
    )
    new_password2 = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords must match"),
        ],
    )
    submit = SubmitField("Reset Password")

    def validate_new_password(self, new_password):
        """Validate password strength."""
        pwd = new_password.data
        if len(pwd) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        if not re.search(r"[A-Z]", pwd):
            raise ValidationError(
                "Password must contain at least one uppercase letter."
            )

        if not re.search(r"[a-z]", pwd):
            raise ValidationError(
                "Password must contain at least one lowercase letter."
            )

        if not re.search(r"\d", pwd):
            raise ValidationError("Password must contain at least one digit.")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', pwd):
            raise ValidationError(
                "Password must contain at least one special character."
            )
