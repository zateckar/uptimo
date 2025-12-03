from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app import db
from .check_result import CheckResult


# Association table for incidents and check results
incident_check_results = db.Table(
    "incident_check_results",
    db.Column(
        "incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True
    ),
    db.Column(
        "check_result_id",
        db.Integer,
        db.ForeignKey("check_result.id"),
        primary_key=True,
    ),
    db.Index("idx_incident_check_result", "incident_id", "check_result_id"),
)


class Incident(db.Model):
    """Incident model for tracking monitor downtime events."""

    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(
        db.Integer, db.ForeignKey("monitor.id"), nullable=False, index=True
    )
    started_at = db.Column(db.DateTime, nullable=False, index=True)
    resolved_at = db.Column(db.DateTime, index=True)
    duration = db.Column(db.Float)  # Duration in seconds
    status = db.Column(
        db.String(20), default="active", nullable=False, index=True
    )  # active, resolved

    # Additional metadata
    description = db.Column(db.Text)
    severity = db.Column(db.String(20), default="critical")  # critical, warning, info

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
    check_results = db.relationship(
        "CheckResult",
        secondary="incident_check_results",
        backref=db.backref("incidents", lazy="dynamic"),
    )

    # Indexes for performance
    __table_args__ = (
        # Existing indexes
        db.Index("idx_incident_monitor_started", "monitor_id", "started_at"),
        db.Index("idx_incident_status_started", "status", "started_at"),
        # Enhanced composite indexes for dashboard performance
        db.Index(
            "idx_incident_monitor_status_started", "monitor_id", "status", "started_at"
        ),
        db.Index("idx_incident_active_started", "status", "started_at"),
        db.Index("idx_incident_resolved_started", "resolved_at", "started_at"),
    )

    def __init__(
        self,
        monitor_id: int,
        status: str = "active",
        started_at: Optional[datetime] = None,
        resolved_at: Optional[datetime] = None,
        duration: Optional[float] = None,
        description: Optional[str] = None,
        severity: str = "critical",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.monitor_id = monitor_id
        self.status = status
        self.started_at = started_at or datetime.now(timezone.utc)
        self.resolved_at = resolved_at
        self.duration = duration
        self.description = description
        self.severity = severity

    def resolve(self) -> bool:
        """Resolve the incident."""
        if self.status != "active":
            return False

        self.resolved_at = datetime.now(timezone.utc)
        self.status = "resolved"
        self.duration = (self.resolved_at - self.started_at).total_seconds()
        self.updated_at = datetime.now(timezone.utc)
        return True

    def is_active(self) -> bool:
        """Check if incident is currently active."""
        return self.status == "active"

    def get_duration_formatted(self) -> str:
        """Get formatted duration string."""
        if not self.duration:
            if self.is_active():
                # Calculate current duration
                # Ensure started_at is timezone-aware
                started_at_utc = self.started_at
                if started_at_utc.tzinfo is None:
                    started_at_utc = started_at_utc.replace(tzinfo=timezone.utc)

                now_utc = datetime.now(timezone.utc)
                self.duration = (now_utc - started_at_utc).total_seconds()
            else:
                return "N/A"

        days = int(self.duration // 86400)
        hours = int((self.duration % 86400) // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def get_affected_checks(self) -> List[CheckResult]:
        """Get all check results during this incident period."""
        # Ensure both datetimes are timezone-aware
        end_time = self.resolved_at if self.resolved_at else datetime.now(timezone.utc)
        started_at = self.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        return (
            CheckResult.query.filter(
                CheckResult.monitor_id == self.monitor_id,
                CheckResult.timestamp >= started_at,
                CheckResult.timestamp <= end_time,
            )
            .order_by(CheckResult.timestamp)
            .all()
        )

    def get_downtime_percentage(self) -> float:
        """Calculate percentage of downtime during this incident."""
        affected_checks = self.get_affected_checks()
        if not affected_checks:
            return 100.0

        down_checks = sum(1 for check in affected_checks if check.status == "down")
        return round((down_checks / len(affected_checks)) * 100, 2)

    def __repr__(self) -> str:
        return f"<Incident {self.id} for Monitor {self.monitor_id} ({self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert incident to dictionary for API responses."""
        return {
            "id": self.id,
            "monitor_id": self.monitor_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "duration": self.duration,
            "duration_formatted": self.get_duration_formatted(),
            "status": self.status,
            "is_active": self.is_active(),
            "description": self.description,
            "severity": self.severity,
            "downtime_percentage": self.get_downtime_percentage()
            if self.is_active()
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
