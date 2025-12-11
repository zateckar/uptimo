from datetime import datetime, timezone

from app import db


class UserIncidentView(db.Model):
    """Track which incidents have been viewed by users."""

    __tablename__ = "user_incident_views"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    incident_id = db.Column(
        db.Integer, db.ForeignKey("incident.id"), nullable=False, index=True
    )
    viewed_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user = db.relationship(
        "User",
        backref=db.backref(
            "incident_views", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    incident = db.relationship(
        "Incident",
        backref=db.backref("views", lazy="dynamic", cascade="all, delete-orphan"),
    )

    # Unique constraint to prevent duplicate views and performance indexes
    __table_args__ = (
        db.UniqueConstraint("user_id", "incident_id", name="unique_user_incident_view"),
        db.Index("idx_user_incident_views_composite", "user_id", "viewed_at"),
        db.Index("idx_user_incident_views_incident_user", "incident_id", "user_id"),
    )

    def __init__(self, user_id: int, incident_id: int):
        self.user_id = user_id
        self.incident_id = incident_id
        self.viewed_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return (
            f"<UserIncidentView user_id={self.user_id} incident_id={self.incident_id}>"
        )
