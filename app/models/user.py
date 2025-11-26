from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager


class User(UserMixin, db.Model):
    """User model for authentication and user management."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_login = db.Column(db.DateTime)

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
        super().__init__(**kwargs)
        self.username = username
        self.email = email
        self.is_admin = is_admin
        self.is_active = is_active

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for API responses."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
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
