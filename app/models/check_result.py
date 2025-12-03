from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional

from app import db
from app.services.deduplication import DeduplicationService


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

    # NEW: Reference fields for deduplication
    error_message_id = db.Column(
        db.Integer, db.ForeignKey("error_messages.id"), nullable=True, index=True
    )
    # Keep additional_data for storing compacted data and non-duplicatable info
    additional_data = db.Column(
        db.Text
    )  # JSON string with compacted data and references

    # Relationships for reference data
    error_message = db.relationship("ErrorMessage", lazy="joined")

    # Indexes for performance
    __table_args__ = (
        # Existing indexes
        db.Index("idx_check_result_monitor_timestamp", "monitor_id", "timestamp"),
        db.Index("idx_check_result_status_timestamp", "status", "timestamp"),
        db.Index("idx_check_result_response_time", "response_time"),
        db.Index("idx_check_result_error_message", "error_message_id"),
        # Enhanced composite indexes for performance
        db.Index(
            "idx_check_result_monitor_status_time", "monitor_id", "status", "timestamp"
        ),
        db.Index(
            "idx_check_result_monitor_success_time", "monitor_id", "timestamp", "status"
        ),
        db.Index("idx_check_result_time_status", "timestamp", "status"),
        # CRITICAL PERFORMANCE INDEXES - High impact, low overhead
        # Uptime calculation optimization - Second most critical query
        # Note: SQLite doesn't support DESC in index definition, handled in query ordering
        db.Index("idx_uptime_calculation", "monitor_id", "timestamp", "status"),
        # Monitor detail loading - Third most critical query
        db.Index("idx_recent_checks", "monitor_id", "timestamp"),
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

        # Handle error message deduplication
        if error_message:
            self.error_message_id = DeduplicationService.get_or_create_error_message(
                error_message
            )

        self.additional_data = additional_data

    def get_error_message(self) -> Optional[str]:
        """Get the full error message, handling both old and new formats."""
        # Try new deduplicated format first
        if self.error_message_id:
            return DeduplicationService.get_error_message_text(self.error_message_id)

        # Fallback for any compatibility issues
        return None

    def set_error_message(self, error_message: Optional[str]) -> None:
        """Set error message using deduplication."""
        if error_message:
            self.error_message_id = DeduplicationService.get_or_create_error_message(
                error_message
            )
        else:
            self.error_message_id = None

    def get_additional_data(self) -> Dict[str, Any]:
        """Parse and return additional data as dict, reconstructing if needed."""
        if not self.additional_data:
            return {}

        # Try to detect if this is compacted format (has reference IDs)
        try:
            data = json.loads(self.additional_data)
            if isinstance(data, dict) and ("cert_id" in data or "domain_id" in data):
                # This is compacted format, reconstruct full data
                return DeduplicationService.reconstruct_additional_data(
                    self.additional_data
                )
            else:
                # This is legacy format, return as-is
                return data
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_additional_data(self, data: Optional[Dict[str, Any]]) -> None:
        """Set additional data using deduplication."""
        if data:
            # Use deduplication service to compact the data
            compacted = DeduplicationService.compact_additional_data(data)
            self.additional_data = compacted
        else:
            self.additional_data = None

    def is_success(self) -> bool:
        """Check if this check result represents a successful check."""
        return self.status == "up"

    def is_timeout(self) -> bool:
        """Check if this check failed due to timeout."""
        error_msg = self.get_error_message()
        return bool(error_msg and "timeout" in error_msg.lower())

    def is_certificate_error(self) -> bool:
        """Check if this check failed due to SSL/TLS certificate issues."""
        error_msg = self.get_error_message()
        return bool(
            error_msg
            and any(
                term in error_msg.lower()
                for term in ["certificate", "ssl", "tls", "verification"]
            )
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
            "error_message": self.get_error_message(),
            "additional_data": self.get_additional_data(),
            "is_success": self.is_success(),
            "is_timeout": self.is_timeout(),
            "is_certificate_error": self.is_certificate_error(),
        }

    @staticmethod
    def to_columnar_dict(check_results: list["CheckResult"]) -> Dict[str, list[Any]]:
        """Convert list of CheckResult objects to columnar dictionary format.

        This format is more compact and compresses better than the traditional
        row-based format. Instead of:
        [{"id": 1, "status": "up"}, {"id": 2, "status": "down"}]

        It produces:
        {"ids": [1, 2], "statuses": ["up", "down"]}

        Args:
            check_results: List of CheckResult objects to convert

        Returns:
            Dictionary with column-based arrays for better compression
        """
        if not check_results:
            return {
                "ids": [],
                "monitor_ids": [],
                "timestamps": [],
                "statuses": [],
                "response_times": [],
                "status_codes": [],
                "error_messages": [],
                "additional_data": [],
                "is_successes": [],
                "is_timeouts": [],
                "is_certificate_errors": [],
            }

        return {
            "ids": [cr.id for cr in check_results],
            "monitor_ids": [cr.monitor_id for cr in check_results],
            "timestamps": [
                cr.timestamp.isoformat() if cr.timestamp else None
                for cr in check_results
            ],
            "statuses": [cr.status for cr in check_results],
            "response_times": [cr.response_time for cr in check_results],
            "status_codes": [cr.status_code for cr in check_results],
            "error_messages": [cr.get_error_message() for cr in check_results],
            "additional_data": [cr.get_additional_data() for cr in check_results],
            "is_successes": [cr.is_success() for cr in check_results],
            "is_timeouts": [cr.is_timeout() for cr in check_results],
            "is_certificate_errors": [
                cr.is_certificate_error() for cr in check_results
            ],
        }

    @staticmethod
    def from_columnar_dict(columnar_data: Dict[str, list[Any]]) -> list["CheckResult"]:
        """Convert columnar dictionary back to list of CheckResult objects.

        This is the inverse operation of to_columnar_dict(), useful for
        testing or when legacy code expects the old format.

        Args:
            columnar_data: Columnar dictionary data from to_columnar_dict()

        Returns:
            List of reconstructed CheckResult objects
        """
        if not columnar_data or not columnar_data.get("ids"):
            return []

        check_results = []
        for i in range(len(columnar_data["ids"])):
            check_result = CheckResult(
                monitor_id=columnar_data["monitor_ids"][i],
                status=columnar_data["statuses"][i],
                response_time=columnar_data["response_times"][i],
                status_code=columnar_data["status_codes"][i],
            )
            check_result.id = columnar_data["ids"][i]

            # Parse timestamp strings
            timestamp_str = columnar_data["timestamps"][i]
            if timestamp_str:
                check_result.timestamp = datetime.fromisoformat(timestamp_str)

            # Set error message if present
            error_msg = columnar_data["error_messages"][i]
            if error_msg:
                check_result.set_error_message(error_msg)

            # Set additional data if present
            additional_data = columnar_data["additional_data"][i]
            if additional_data:
                check_result.set_additional_data(additional_data)

            check_results.append(check_result)

        return check_results

    def __repr__(self) -> str:
        return f"<CheckResult {self.monitor_id}:{self.status} at {self.timestamp}>"
