"""Public status page model for Uptimo."""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from app import db


class PublicStatusPage(db.Model):
    """Public status page configuration per user."""

    __tablename__ = "public_status_pages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    uuid = db.Column(
        db.String(100), unique=True, nullable=False, index=True
    )  # UUID v4 + extra randomness
    url_type = db.Column(
        db.String(20), default="uuid", nullable=False
    )  # "uuid" or "simple"
    custom_header = db.Column(db.String(200))
    description = db.Column(db.Text)
    selected_monitors = db.Column(db.Text)  # JSON array of monitor IDs
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = db.relationship("User", backref="public_status_pages")

    # Indexes for performance
    __table_args__ = (
        db.Index("idx_public_status_user_active", "user_id", "is_active"),
        db.Index("idx_public_status_uuid_active", "uuid", "is_active"),
    )

    def __init__(
        self,
        user_id: int,
        url_type: str = "uuid",
        custom_header: Optional[str] = None,
        description: Optional[str] = None,
        selected_monitors: Optional[List[int]] = None,
        is_active: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.user_id = user_id
        self.url_type = url_type
        self.custom_header = custom_header
        self.description = description
        self.selected_monitors = (
            json.dumps(selected_monitors or []) if selected_monitors else None
        )
        self.is_active = is_active
        self.uuid = self._generate_secure_uuid()

    @staticmethod
    def _generate_secure_uuid() -> str:
        """Generate a secure UUID v4 with extra randomness for privacy.

        Returns a UUID string formatted as standard UUID v4 plus
        additional random characters for enhanced security.
        """
        # Generate UUID v4
        base_uuid = str(uuid.uuid4())

        # Add extra randomness (16 additional characters)
        extra_random = str(uuid.uuid4()).replace("-", "")[:16]

        # Combine for 50+ character secure identifier
        return f"{base_uuid}-{extra_random}"

    def get_selected_monitor_ids(self) -> List[int]:
        """Get list of selected monitor IDs from JSON storage."""
        if not self.selected_monitors:
            return []

        try:
            return json.loads(self.selected_monitors)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_selected_monitors(self, monitor_ids: List[int]) -> None:
        """Set selected monitor IDs as JSON."""
        self.selected_monitors = json.dumps(monitor_ids if monitor_ids else [])

    def get_public_url(self, base_url: str = "") -> str:
        """Get the public URL for this status page."""
        if self.url_type == "simple":
            return f"{base_url}/status"
        else:
            return f"{base_url}/status/{self.uuid}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "uuid": self.uuid,
            "url_type": self.url_type,
            "custom_header": self.custom_header,
            "description": self.description,
            "selected_monitors": self.get_selected_monitor_ids(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<PublicStatusPage id={self.id} user_id={self.user_id} "
            f"uuid={self.uuid[:8]}... active={self.is_active}>"
        )
