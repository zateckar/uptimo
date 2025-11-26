from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional

from app import db


class CheckResult(db.Model):
    """Check result model for storing monitor check outcomes."""

    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(
        db.Integer, db.ForeignKey("monitor.id"), nullable=False, index=True
    )
    timestamp = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(20), nullable=False, index=True)  # up, down, unknown
    response_time = db.Column(db.Float, index=True)  # Response time in milliseconds
    status_code = db.Column(db.Integer)  # HTTP status code for web checks
    error_message = db.Column(db.Text)

    # Additional data stored as JSON
    additional_data = db.Column(
        db.Text
    )  # JSON string for additional check-specific data

    # Indexes for performance
    __table_args__ = (
        db.Index("idx_check_result_monitor_timestamp", "monitor_id", "timestamp"),
        db.Index("idx_check_result_status_timestamp", "status", "timestamp"),
        db.Index("idx_check_result_response_time", "response_time"),
    )

    def __init__(
        self,
        monitor_id: int,
        status: str,
        timestamp: Optional[datetime] = None,
        response_time: Optional[float] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        additional_data: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.monitor_id = monitor_id
        self.status = status
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.response_time = response_time
        self.status_code = status_code
        self.error_message = error_message
        self.additional_data = additional_data

    def get_additional_data(self) -> Dict[str, Any]:
        """Parse and return additional data as dict."""
        if not self.additional_data:
            return {}

        try:
            return json.loads(self.additional_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_additional_data(self, data: Optional[Dict[str, Any]]) -> None:
        """Set additional data from dict."""
        if data:
            self.additional_data = json.dumps(data)
        else:
            self.additional_data = None

    def is_success(self) -> bool:
        """Check if this check result represents a successful check."""
        return self.status == "up"

    def is_timeout(self) -> bool:
        """Check if this check failed due to timeout."""
        return self.error_message and "timeout" in self.error_message.lower()

    def is_certificate_error(self) -> bool:
        """Check if this check failed due to SSL/TLS certificate issues."""
        return self.error_message and any(
            term in self.error_message.lower()
            for term in ["certificate", "ssl", "tls", "verification"]
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert check result to dictionary for API responses."""
        return {
            "id": self.id,
            "monitor_id": self.monitor_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "response_time": self.response_time,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "additional_data": self.get_additional_data(),
            "is_success": self.is_success(),
            "is_timeout": self.is_timeout(),
            "is_certificate_error": self.is_certificate_error(),
        }

    def __repr__(self) -> str:
        return f"<CheckResult {self.monitor_id}:{self.status} at {self.timestamp}>"
