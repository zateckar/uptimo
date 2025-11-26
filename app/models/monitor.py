from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app import db
from .check_result import CheckResult
from .incident import Incident


class MonitorType(Enum):
    """Monitor type enumeration."""

    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    PING = "ping"
    KAFKA = "kafka"


class CheckInterval(Enum):
    """Check interval enumeration in seconds."""

    THIRTY_SECONDS = 30
    ONE_MINUTE = 60
    FIVE_MINUTES = 300
    FIFTEEN_MINUTES = 900
    THIRTY_MINUTES = 1800
    ONE_HOUR = 3600


class Monitor(db.Model):
    """Monitor model for tracking various endpoints and services."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.Enum(MonitorType), nullable=False, index=True)
    target = db.Column(db.String(500), nullable=False)  # URL, IP, hostname, etc.
    port = db.Column(db.Integer)  # For TCP checks
    check_interval = db.Column(
        db.Enum(CheckInterval), default=CheckInterval.FIVE_MINUTES, nullable=False
    )
    timeout = db.Column(db.Integer, default=30)  # Timeout in seconds

    # Outage criteria
    expected_status_codes = db.Column(
        db.Text
    )  # JSON array of expected HTTP status codes
    response_time_threshold = db.Column(db.Integer)  # Response time threshold in ms
    string_match = db.Column(db.String(500))  # String to match in response
    string_match_type = db.Column(
        db.String(20), default="contains"
    )  # contains, not_contains, regex
    json_path_match = db.Column(db.String(500))  # JSON path and expected value

    # HTTP-specific settings
    http_method = db.Column(db.String(10), default="GET")  # GET, POST, PUT, PATCH, HEAD
    http_headers = db.Column(db.Text)  # JSON object of custom headers
    http_body = db.Column(db.Text)  # Request body for POST/PUT/PATCH

    # TLS/SSL settings
    verify_ssl = db.Column(db.Boolean, default=True)
    check_cert_expiration = db.Column(db.Boolean, default=True)
    cert_expiration_threshold = db.Column(
        db.Integer, default=30
    )  # Days before expiration to warn

    # mTLS settings for HTTPS
    http_ssl_ca_cert = db.Column(db.Text)  # PEM content for CA certificate
    http_ssl_client_cert = db.Column(db.Text)  # PEM content for client certificate
    http_ssl_client_key = db.Column(db.Text)  # PEM content for client private key

    # Domain settings
    check_domain = db.Column(db.Boolean, default=True)
    expected_domain = db.Column(db.String(500))

    # Kafka-specific settings
    kafka_security_protocol = db.Column(
        db.String(20), default="PLAINTEXT"
    )  # PLAINTEXT, SSL, SASL_SSL, SASL_PLAINTEXT
    kafka_sasl_mechanism = db.Column(
        db.String(20)
    )  # PLAIN, SCRAM-SHA-256, SCRAM-SHA-512, OAUTHBEARER
    kafka_sasl_username = db.Column(db.String(500))
    kafka_sasl_password = db.Column(db.String(500))
    kafka_oauth_token_url = db.Column(db.String(500))
    kafka_oauth_client_id = db.Column(db.String(500))
    kafka_oauth_client_secret = db.Column(db.String(500))
    kafka_ssl_ca_cert = db.Column(db.Text)  # PEM content
    kafka_ssl_client_cert = db.Column(db.Text)  # PEM content
    kafka_ssl_client_key = db.Column(db.Text)  # PEM content
    kafka_topic = db.Column(db.String(500))  # Topic for read/write operations
    kafka_consumer_group = db.Column(
        db.String(500)
    )  # Consumer group for reading messages
    kafka_read_message = db.Column(db.Boolean, default=False)
    kafka_write_message = db.Column(db.Boolean, default=False)
    kafka_message_payload = db.Column(db.Text)  # JSON payload to write
    kafka_autocommit = db.Column(db.Boolean, default=False)

    # Status and metadata
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    last_check = db.Column(db.DateTime)
    last_status = db.Column(db.String(20), default="unknown")  # up, down, unknown
    last_response_time = db.Column(db.Float)  # in milliseconds
    consecutive_failures = db.Column(
        db.Integer, default=0
    )  # Track consecutive DOWN checks

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
        "CheckResult", backref="monitor", lazy="dynamic", cascade="all, delete-orphan"
    )
    incidents = db.relationship(
        "Incident", backref="monitor", lazy="dynamic", cascade="all, delete-orphan"
    )
    notification_settings = db.relationship(
        "MonitorNotification",
        backref="monitor",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # Indexes for performance
    __table_args__ = (
        db.Index("idx_monitor_user_active", "user_id", "is_active"),
        db.Index("idx_monitor_type_active", "type", "is_active"),
    )

    def __init__(
        self,
        user_id: int,
        name: str,
        type: MonitorType,
        target: str,
        port: Optional[int] = None,
        check_interval: CheckInterval = CheckInterval.FIVE_MINUTES,
        timeout: int = 30,
        expected_status_codes: Optional[str] = None,
        response_time_threshold: Optional[int] = None,
        string_match: Optional[str] = None,
        string_match_type: str = "contains",
        json_path_match: Optional[str] = None,
        http_method: str = "GET",
        http_headers: Optional[str] = None,
        http_body: Optional[str] = None,
        verify_ssl: bool = True,
        check_cert_expiration: bool = True,
        cert_expiration_threshold: int = 30,
        http_ssl_ca_cert: Optional[str] = None,
        http_ssl_client_cert: Optional[str] = None,
        http_ssl_client_key: Optional[str] = None,
        check_domain: bool = True,
        expected_domain: Optional[str] = None,
        kafka_security_protocol: str = "PLAINTEXT",
        kafka_sasl_mechanism: Optional[str] = None,
        kafka_sasl_username: Optional[str] = None,
        kafka_sasl_password: Optional[str] = None,
        kafka_oauth_token_url: Optional[str] = None,
        kafka_oauth_client_id: Optional[str] = None,
        kafka_oauth_client_secret: Optional[str] = None,
        kafka_ssl_ca_cert: Optional[str] = None,
        kafka_ssl_client_cert: Optional[str] = None,
        kafka_ssl_client_key: Optional[str] = None,
        kafka_topic: Optional[str] = None,
        kafka_consumer_group: Optional[str] = None,
        kafka_read_message: bool = False,
        kafka_write_message: bool = False,
        kafka_message_payload: Optional[str] = None,
        kafka_autocommit: bool = False,
        is_active: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.user_id = user_id
        self.name = name
        self.type = type
        self.target = target
        self.port = port
        self.check_interval = check_interval
        self.timeout = timeout
        self.expected_status_codes = expected_status_codes
        self.response_time_threshold = response_time_threshold
        self.string_match = string_match
        self.string_match_type = string_match_type
        self.json_path_match = json_path_match
        self.http_method = http_method
        self.http_headers = http_headers
        self.http_body = http_body
        self.verify_ssl = verify_ssl
        self.check_cert_expiration = check_cert_expiration
        self.cert_expiration_threshold = cert_expiration_threshold
        self.http_ssl_ca_cert = http_ssl_ca_cert
        self.http_ssl_client_cert = http_ssl_client_cert
        self.http_ssl_client_key = http_ssl_client_key
        self.check_domain = check_domain
        self.expected_domain = expected_domain
        self.kafka_security_protocol = kafka_security_protocol
        self.kafka_sasl_mechanism = kafka_sasl_mechanism
        self.kafka_sasl_username = kafka_sasl_username
        self.kafka_sasl_password = kafka_sasl_password
        self.kafka_oauth_token_url = kafka_oauth_token_url
        self.kafka_oauth_client_id = kafka_oauth_client_id
        self.kafka_oauth_client_secret = kafka_oauth_client_secret
        self.kafka_ssl_ca_cert = kafka_ssl_ca_cert
        self.kafka_ssl_client_cert = kafka_ssl_client_cert
        self.kafka_ssl_client_key = kafka_ssl_client_key
        self.kafka_topic = kafka_topic
        self.kafka_consumer_group = kafka_consumer_group
        self.kafka_read_message = kafka_read_message
        self.kafka_write_message = kafka_write_message
        self.kafka_message_payload = kafka_message_payload
        self.kafka_autocommit = kafka_autocommit
        self.is_active = is_active

    def get_uptime_percentage(self, days: int = 7) -> float:
        """Calculate uptime percentage for the last N days.

        Paused periods are automatically excluded because checks are only
        created when the monitor is active (is_active=True). This method
        counts successful checks vs total checks, where all checks were
        created during active periods.

        Args:
            days: Number of days to look back

        Returns:
            Uptime percentage (0-100) rounded to 2 decimal places
        """
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        total_checks = self.check_results.filter(
            CheckResult.timestamp >= start_time
        ).count()
        if total_checks == 0:
            return 0.0

        successful_checks = self.check_results.filter(
            CheckResult.timestamp >= start_time, CheckResult.status == "up"
        ).count()

        return round((successful_checks / total_checks) * 100, 2)

    def get_average_response_time(self, hours: int = 24) -> float:
        """Get average response time for the last N hours."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        results = self.check_results.filter(
            CheckResult.timestamp >= start_time,
            CheckResult.status == "up",
            CheckResult.response_time.isnot(None),
        ).all()

        if not results:
            return 0.0

        avg_time = sum(
            r.response_time for r in results if r.response_time is not None
        ) / len(results)
        return round(avg_time, 2)

    def get_recent_checks(self, count: int = 10) -> List[CheckResult]:
        """Get most recent check results."""
        return (
            self.check_results.order_by(CheckResult.timestamp.desc()).limit(count).all()
        )

    def get_checks_by_timespan(self, hours: int) -> List[CheckResult]:
        """Get check results for the specified timespan in hours."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (
            self.check_results.filter(CheckResult.timestamp >= start_time)
            .order_by(CheckResult.timestamp.desc())
            .all()
        )

    def get_current_status(self) -> Tuple[str, Optional[datetime]]:
        """Get current status with timestamp."""
        if not self.last_check:
            # For new monitors that haven't been checked yet,
            # we should consider them as "unknown" rather than assuming they're down
            return "unknown", None

        # Ensure last_check is timezone-aware for comparison
        last_check_utc = self.last_check
        if last_check_utc.tzinfo is None:
            last_check_utc = last_check_utc.replace(tzinfo=timezone.utc)

        # If last check was more than 10 intervals ago, consider it stale
        # Increased from 5 to 10 to reduce false "unknown" classifications
        check_interval_seconds = (
            self.check_interval.value if self.check_interval else 300
        )
        time_since_last_check = datetime.now(timezone.utc) - last_check_utc

        if time_since_last_check > timedelta(seconds=check_interval_seconds * 10):
            # Only mark as unknown if it's been stale for a long time
            return "unknown", self.last_check
        elif time_since_last_check > timedelta(seconds=check_interval_seconds * 3):
            # If it's been 3+ intervals, we're less certain but keep the last known status
            # This prevents frequent flapping between up/down/unknown
            return self.last_status, self.last_check

        # If recently checked, use the actual last status
        return self.last_status, self.last_check

    def is_up(self) -> bool:
        """Check if monitor is currently up."""
        status, _ = self.get_current_status()
        return status == "up"

    def is_down(self) -> bool:
        """Check if monitor is currently down."""
        status, _ = self.get_current_status()
        return status == "down"

    def is_unknown(self) -> bool:
        """Check if monitor status is unknown."""
        status, _ = self.get_current_status()
        return status == "unknown"

    def get_active_incident(self) -> Optional[Incident]:
        """Get currently active incident if any."""
        return self.incidents.filter_by(resolved_at=None).first()

    def update_status(
        self,
        status: str,
        response_time: Optional[float] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update monitor status after a check."""
        previous_status = self.last_status

        self.last_check = datetime.now(timezone.utc)
        self.last_status = status
        self.last_response_time = response_time
        self.updated_at = datetime.now(timezone.utc)

        # Invalidate favicon cache if status changed
        if previous_status != status:
            from app import invalidate_favicon_cache

            invalidate_favicon_cache(self.user_id)

        # Track consecutive failures
        if status == "down":
            self.consecutive_failures = (self.consecutive_failures or 0) + 1
        else:
            self.consecutive_failures = 0

        # Create check result record
        check_result = CheckResult(
            monitor_id=self.id,
            timestamp=datetime.now(timezone.utc),
            status=status,
            response_time=response_time,
            status_code=status_code,
            error_message=error_message,
        )

        # Set additional data if provided
        if additional_data:
            check_result.set_additional_data(additional_data)

        db.session.add(check_result)

        # Check if we need to create or resolve an incident
        self._handle_incidents(status, previous_status)

        db.session.commit()

    def _handle_incidents(self, current_status: str, previous_status: str) -> None:
        """Handle incident creation and resolution."""
        from app.notification.service import notification_service

        active_incident = self.get_active_incident()

        # Only create incident and send notification after first failure
        # Notification service will check consecutive_failures threshold
        if (
            current_status == "down"
            and not active_incident
            and previous_status != "down"
        ):
            # Get the latest check result to extract error message
            latest_check = self.check_results.order_by(
                CheckResult.timestamp.desc()
            ).first()

            error_message = None
            if latest_check and latest_check.error_message:
                error_message = latest_check.error_message
            elif latest_check and latest_check.status_code:
                error_message = f"HTTP {latest_check.status_code}"

            # Create new incident with description (reason for outage)
            incident = Incident(
                monitor_id=self.id,
                started_at=datetime.now(timezone.utc),
                status="active",
                description=error_message,
            )
            db.session.add(incident)
            db.session.flush()  # Get the incident ID

            # Send notification for going down
            title = f"Monitor Down: {self.name}"
            message = (
                f"Monitor '{self.name}' ({self.type.value.upper()} - {self.target}) "
                f"is down. Started: {incident.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            if error_message:
                message += f"\n\nReason: {error_message}"

            notification_service.send_monitor_notification(
                monitor=self,
                event_type="down",
                title=title,
                message=message,
                incident=incident,
            )

        elif current_status == "up" and active_incident:
            # Resolve existing incident
            active_incident.resolved_at = datetime.now(timezone.utc)
            active_incident.status = "resolved"
            # Ensure both datetimes are timezone-aware for subtraction
            started_at = active_incident.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            active_incident.duration = (
                active_incident.resolved_at - started_at
            ).total_seconds()

            # Send notification for coming back up
            title = f"Monitor Recovered: {self.name}"
            message = (
                f"Monitor '{self.name}' ({self.type.value.upper()} - {self.target}) "
                f"is back up after {active_incident.get_duration_formatted()} of downtime. "
                f"Resolved: {active_incident.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )

            notification_service.send_monitor_notification(
                monitor=self,
                event_type="up",
                title=title,
                message=message,
                incident=active_incident,
            )

    def __repr__(self) -> str:
        return f"<Monitor {self.name} ({self.type.value})>"

    def to_dict(
        self, include_recent_checks: bool = False, include_incidents: bool = False
    ) -> Dict[str, Any]:
        """Convert monitor to dictionary for API responses."""
        data = {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "target": self.target,
            "port": self.port,
            "check_interval": self.check_interval.value
            if self.check_interval
            else None,
            "timeout": self.timeout,
            "verify_ssl": self.verify_ssl,
            "check_cert_expiration": self.check_cert_expiration,
            "cert_expiration_threshold": self.cert_expiration_threshold,
            "check_domain": self.check_domain,
            "expected_domain": self.expected_domain,
            "kafka_security_protocol": self.kafka_security_protocol,
            "is_active": self.is_active,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_status": self.last_status,
            "last_response_time": self.last_response_time,
            "uptime_24h": self.get_uptime_percentage(1),
            "uptime_7d": self.get_uptime_percentage(7),
            "uptime_30d": self.get_uptime_percentage(30),
            "avg_response_time_24h": self.get_average_response_time(24),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_recent_checks:
            data["recent_checks"] = [
                check.to_dict() for check in self.get_recent_checks(30)
            ]

        if include_incidents:
            data["incidents"] = [
                incident.to_dict()
                for incident in self.incidents.order_by(
                    Incident.started_at.desc()
                ).limit(10)
            ]

        return data
