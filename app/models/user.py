from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager


class User(UserMixin, db.Model):
    """User model for authentication and user management."""

    id = db.Column(db.Integer, primary_key=True)
    auth_type = db.Column(db.String(20), nullable=False, default="local", index=True)
    oidc_provider = db.Column(db.String(100), nullable=True, index=True)
    oidc_subject = db.Column(db.String(255), nullable=True, index=True)

    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OIDC users
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_login = db.Column(db.DateTime)

    # Add composite index for OIDC identity lookup
    __table_args__ = (
        db.Index("idx_oidc_identity", "oidc_provider", "oidc_subject"),
        {"extend_existing": True},
    )

    # Relationships
    monitors = db.relationship(
        "Monitor", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    notification_channels = db.relationship(
        "NotificationChannel",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __init__(
        self,
        username: str,
        email: str,
        is_admin: bool = False,
        is_active: bool = True,
        **kwargs: Any,
    ) -> None:
        # Set is_active through kwargs to avoid direct assignment
        if "is_active" not in kwargs:
            kwargs["is_active"] = is_active
        if "is_admin" not in kwargs:
            kwargs["is_admin"] = is_admin

        super().__init__(**kwargs)
        self.username = username
        self.email = email

    def set_password(self, password: str) -> None:
        """Set password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)

    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login = datetime.now(timezone.utc)
        db.session.commit()

    def get_monitor_count(self) -> int:
        """Get total number of monitors for this user."""
        return self.monitors.count()

    def get_active_monitor_count(self) -> int:
        """Get number of active monitors for this user."""
        return self.monitors.filter_by(is_active=True).count()

    def __repr__(self) -> str:
        return f"<User {self.username}>"

    def is_oidc_user(self) -> bool:
        """Check if user is OIDC-authenticated."""
        return self.auth_type == "oidc"

    def has_password(self) -> bool:
        """Check if user has a local password."""
        return self.auth_type == "local" and self.password_hash is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for API responses."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "auth_type": self.auth_type,
            "oidc_provider": self.oidc_provider,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "monitor_count": self.get_monitor_count(),
            "active_monitor_count": self.get_active_monitor_count(),
        }


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))
