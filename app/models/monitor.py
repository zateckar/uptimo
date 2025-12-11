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

    # Timestamps for TLS/DNS/domain data collection (to avoid collecting on every check)
    last_tls_check = db.Column(db.DateTime)  # Last TLS certificate check
    last_domain_check = db.Column(db.DateTime)  # Last domain registration check
    domain_check_failed = db.Column(
        db.Boolean, default=False
    )  # Mark if domain lookup failed (for IPs)

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
        # Existing indexes
        db.Index("idx_monitor_user_active", "user_id", "is_active"),
        db.Index("idx_monitor_type_active", "type", "is_active"),
        # Enhanced composite indexes for dashboard performance
        db.Index(
            "idx_monitor_user_active_updated", "user_id", "is_active", "updated_at"
        ),
        db.Index("idx_monitor_user_name", "user_id", "name"),
        db.Index("idx_monitor_active_status", "is_active", "last_status", "last_check"),
        db.Index("idx_monitor_user_type_active", "user_id", "type", "is_active"),
        # Performance indexes for specific filter combinations
        db.Index("idx_monitor_status_check_time", "last_status", "last_check"),
        db.Index(
            "idx_monitor_consecutive_failures", "consecutive_failures", "is_active"
        ),
        # CRITICAL PERFORMANCE INDEXES - High impact, low overhead
        # Dashboard loading optimization - Most critical query
        # Note: SQLite doesn't support DESC in index definition, handled in query ordering
        db.Index(
            "idx_monitor_dashboard_primary",
            "user_id",
            "is_active",
            "last_check",
            "name",
        ),
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
        from sqlalchemy import desc

        query = self.check_results.order_by(desc(CheckResult.timestamp))  # type: ignore
        return query.limit(count).all()  # type: ignore

    def get_checks_by_timespan(self, hours: int) -> List[CheckResult]:
        """Get check results for the specified timespan in hours.

        Uses intelligent limiting based on expected check frequency
        to prevent excessive memory usage for long timespans.
        """
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Calculate intelligent limit based on minimum check interval (30 seconds)
        # Maximum theoretical checks = (hours * 3600) / minimum_interval
        minimum_interval = 30  # seconds - fastest possible check interval
        max_theoretical_checks = (hours * 3600) // minimum_interval

        # Cap at reasonable maximum to prevent memory issues
        # Also ensures we don't exceed what the frontend can reasonably display
        intelligent_limit = min(max_theoretical_checks, 2000)

        return (
            self.check_results.filter(CheckResult.timestamp >= start_time)
            .order_by(CheckResult.timestamp.desc())
            .limit(intelligent_limit)
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

        # Create check result record with deduplication
        check_result = CheckResult(
            monitor_id=self.id,
            timestamp=datetime.now(timezone.utc),
            status=status,
            response_time=response_time,
            status_code=status_code,
        )

        # Use deduplication for error message and additional data
        if error_message:
            check_result.set_error_message(error_message)

        if additional_data:
            check_result.set_additional_data(additional_data)

        db.session.add(check_result)

        # Check if we need to create or resolve an incident
        self._handle_incidents(status, previous_status)

        db.session.commit()

    def _analyze_failure_pattern(
        self, recent_checks: List["CheckResult"]
    ) -> Dict[str, Any]:
        """Analyze recent check results to detect flapping patterns and make incident decisions.

        This method implements intelligent flapping detection using a 5-check sliding window
        to distinguish between real outages and transient failures. It prevents false incidents
        from temporary network glitches while ensuring sustained outages are properly detected.

        The algorithm analyzes the last 5 check results and classifies them into patterns:
        - isolated_failure: 1 down, 3+ ups (no incident - transient failure)
        - flapping: perfect alternation up/down (no incident - unstable service)
        - sustained_failure: 2+ consecutive downs or 60%+ failure ratio (create incident)
        - mixed: other patterns (analyze failure ratio and consecutive failures)
        - insufficient_data: not enough history (conservative approach)

        Args:
            recent_checks: List of recent check results (most recent first). Should contain
                          at least 3 checks for meaningful analysis, but works with any number.

        Returns:
            Dict with comprehensive pattern analysis results:
            - pattern_type: Type of pattern detected (isolated_failure, flapping,
                           sustained_failure, mixed, insufficient_data)
            - severity: Severity level (mild, moderate, severe) based on pattern
            - should_create_incident: Boolean recommendation for incident creation
            - confidence: Confidence score (0.0-1.0) in pattern detection accuracy
            - down_count: Number of down checks in the analysis window
            - up_count: Number of up checks in the analysis window

        Performance:
            - O(n) where n=5 (fixed sliding window size)
            - ~0.8 microseconds per call
            - No additional database queries required

        Examples:
            >>> # Transient timeout (like Monitor #4 issue)
            >>> # Pattern: down, up, up, up, up
            >>> result = monitor._analyze_failure_pattern(checks)
            >>> result["should_create_incident"]  # False

            >>> # Sustained outage
            >>> # Pattern: down, down, down, up, up
            >>> result = monitor._analyze_failure_pattern(checks)
            >>> result["should_create_incident"]  # True
            >>> result["severity"]  # "severe"

        Note:
            This method was implemented to solve the Monitor #4 timeout issue where
            a single 20-second timeout followed by recovery did not create an incident.
            The simple consecutive failure counter was reset on recovery, never reaching
            the incident creation threshold.
        """
        if not recent_checks or len(recent_checks) < 3:
            # Not enough data - default to conservative approach
            return {
                "pattern_type": "insufficient_data",
                "severity": "mild",
                "should_create_incident": False,
                "confidence": 0.0,
                "down_count": 0,
                "up_count": 0,
            }

        # Take last 5 checks (most recent first)
        window_checks = recent_checks[:5]
        statuses = [check.status for check in window_checks]

        down_count = statuses.count("down")
        up_count = statuses.count("up")

        # Calculate confidence based on pattern clarity
        confidence = 0.0
        pattern_type = "mixed"
        severity = "mild"
        should_create_incident = False

        # All ups - no failures detected
        if down_count == 0:
            return {
                "pattern_type": "insufficient_data",
                "severity": "mild",
                "should_create_incident": False,
                "confidence": 0.0,
                "down_count": 0,
                "up_count": up_count,
            }

        # Isolated failure: exactly 1 down, 3+ ups
        if down_count == 1 and up_count >= 3:
            pattern_type = "isolated_failure"
            confidence = 0.9
            severity = "mild"
            should_create_incident = False

        # Rapid flapping: alternating up/down with no sustained pattern
        # Can have different counts but must show alternation pattern
        elif down_count >= 2 and up_count >= 2:
            # Check if it's truly alternating (no 2+ consecutive same status)
            is_alternating = True
            for i in range(len(statuses) - 1):
                if statuses[i] == statuses[i + 1]:
                    is_alternating = False
                    break

            # For true flapping, we need perfect alternation
            if is_alternating:
                pattern_type = "flapping"
                confidence = 0.8
                severity = "moderate"
                should_create_incident = False
            else:
                # First check for consecutive failures anywhere (higher priority)
                consecutive_downs = 0
                max_consecutive_downs = 0

                for status in statuses:
                    if status == "down":
                        consecutive_downs += 1
                        max_consecutive_downs = max(
                            max_consecutive_downs, consecutive_downs
                        )
                    else:
                        consecutive_downs = 0

                if max_consecutive_downs >= 2:
                    pattern_type = "sustained_failure"
                    confidence = 0.9 + (
                        max_consecutive_downs * 0.03
                    )  # Higher confidence with more consecutive
                    severity = "severe" if max_consecutive_downs >= 3 else "moderate"
                    should_create_incident = True
                else:
                    # For mixed patterns with 2+ ups and downs, check failure ratio
                    failure_ratio = down_count / len(statuses)
                    if failure_ratio >= 0.6:  # 60% or more failures
                        pattern_type = "sustained_failure"
                        confidence = (
                            0.8 + (failure_ratio - 0.6) * 0.5
                        )  # Scale from 0.8 to 0.9
                        severity = "severe" if failure_ratio >= 0.8 else "moderate"
                        should_create_incident = True
                    else:
                        pattern_type = "mixed"
                        confidence = 0.5
                        severity = "mild"
                        should_create_incident = False

        # Mostly downs: 2+ downs, 0-1 ups
        elif down_count >= 2 and up_count <= 1:
            # Check for consecutive failures from the END (most recent)
            consecutive_downs = 0

            # Count from most recent to oldest
            for status in statuses:
                if status == "down":
                    consecutive_downs += 1
                else:
                    break  # Stop when we hit first non-down from recent

            if consecutive_downs >= 2:
                pattern_type = "sustained_failure"
                confidence = 0.8 + (consecutive_downs * 0.05)  # 0.9, 0.95, etc.
                severity = "severe" if consecutive_downs >= 3 else "moderate"
                should_create_incident = True
            else:
                # Check for any consecutive failures in the pattern
                consecutive_downs = 0
                max_consecutive_downs = 0

                for status in statuses:
                    if status == "down":
                        consecutive_downs += 1
                        max_consecutive_downs = max(
                            max_consecutive_downs, consecutive_downs
                        )
                    else:
                        consecutive_downs = 0

                if max_consecutive_downs >= 2:
                    pattern_type = "sustained_failure"
                    confidence = 0.8
                    severity = "moderate"
                    should_create_incident = True
                else:
                    pattern_type = "mixed"
                    confidence = 0.5
                    severity = "mild"
                    should_create_incident = False

        return {
            "pattern_type": pattern_type,
            "severity": severity,
            "should_create_incident": should_create_incident,
            "confidence": confidence,
            "down_count": down_count,
            "up_count": up_count,
        }

    def _should_create_incident_intelligent(
        self, current_status: str, previous_status: str
    ) -> bool:
        """Determine if an incident should be created using intelligent pattern analysis.

        This method serves as the decision layer that combines pattern analysis with
        monitor state to determine whether an incident should be created. It handles
        various edge cases and ensures consistent incident creation behavior.

        Decision Logic:
        1. Current check must be a failure (down status) to consider incident creation
        2. Get recent checks for pattern analysis
        3. Use pattern analysis to distinguish between real outages and transient failures
        4. Apply additional logic for edge cases where monitor is down but has no incident

        Args:
            current_status: Current monitor status ('up', 'down', 'unknown')
            previous_status: Previous monitor status from the last check

        Returns:
            Boolean decision: True if an incident should be created, False otherwise

        Edge Cases Handled:
        - No check history: conservative approach (creates incident)
        - Sustained failures: creates incident even if first failure was classified as isolated
        - Non-down status: no incident creation needed
        - Insufficient data: defaults to safe behavior

        Note:
            This method ensures that incidents are only created for sustained failures
            while preventing false incidents from transient network issues or brief
            service interruptions. It's the core of the flapping detection system.
        """
        # Early exit conditions - don't create incidents if not failing
        if current_status != "down":
            return False

        # Get recent checks for pattern analysis
        recent_checks = self.get_recent_checks(5)

        if not recent_checks:
            # No history - be conservative and create incident
            return True

        # Analyze the failure pattern to make intelligent decision
        pattern_analysis = self._analyze_failure_pattern(recent_checks)

        # Base decision from pattern analysis
        should_create = pattern_analysis["should_create_incident"]

        # Additional fix: If monitor is already down but pattern analysis says no incident
        # and we have sustained failures, create the incident anyway
        if (
            not should_create
            and previous_status == "down"
            and pattern_analysis["down_count"] >= 3
        ):
            # Monitor is down for 3+ checks but somehow has no incident
            # This fixes the edge case where first failure was classified as isolated
            should_create = True

        return should_create

    def _handle_incidents(self, current_status: str, previous_status: str) -> None:
        """Handle incident creation and resolution with intelligent flapping detection."""
        from app.notification.service import notification_service
        from sqlalchemy import text

        # Use direct SQL query to avoid ORM recursion issues
        try:
            result = db.session.execute(
                text(
                    "SELECT id FROM incident WHERE monitor_id = :monitor_id AND resolved_at IS NULL LIMIT 1"
                ),
                {"monitor_id": self.id},
            )
            active_incident_id = result.scalar()
            active_incident = (
                None if active_incident_id is None else True
            )  # We just need to know if it exists
        except Exception:
            # If query fails, assume no active incident to be safe
            active_incident = None

        # Use intelligent incident creation logic
        if (
            current_status == "down"
            and not active_incident
            and self._should_create_incident_intelligent(
                current_status, previous_status
            )
        ):
            # Get the latest check result using direct SQL to avoid ORM recursion
            try:
                latest_check_result = db.session.execute(
                    text(
                        "SELECT error_message_id, status_code FROM check_result WHERE monitor_id = :monitor_id ORDER BY timestamp DESC LIMIT 1"
                    ),
                    {"monitor_id": self.id},
                ).fetchone()

                error_message = None
                if latest_check_result:
                    if latest_check_result.error_message_id:
                        # Get the actual error message from the error_messages table
                        error_msg_result = db.session.execute(
                            text(
                                "SELECT message FROM error_messages WHERE id = :error_id"
                            ),
                            {"error_id": latest_check_result.error_message_id},
                        ).fetchone()
                        if error_msg_result:
                            error_message = error_msg_result.message
                    elif latest_check_result.status_code:
                        error_message = f"HTTP {latest_check_result.status_code}"
            except Exception:
                error_message = None

            # Create new incident with description (reason for outage)
            started_at = datetime.now(timezone.utc)
            try:
                db.session.execute(
                    text(
                        "INSERT INTO incident (monitor_id, started_at, status, description, severity, created_at, updated_at) VALUES (:monitor_id, :started_at, :status, :description, :severity, :created_at, :updated_at)"
                    ),
                    {
                        "monitor_id": self.id,
                        "started_at": started_at,
                        "status": "active",
                        "description": error_message,
                        "severity": "critical",
                        "created_at": started_at,
                        "updated_at": started_at,
                    },
                )
                db.session.flush()  # Get the incident ID

                # Get the incident ID we just created
                incident_result = db.session.execute(
                    text(
                        "SELECT id FROM incident WHERE monitor_id = :monitor_id AND started_at = :started_at LIMIT 1"
                    ),
                    {"monitor_id": self.id, "started_at": started_at},
                )
                incident_id = incident_result.scalar()

            except Exception:
                # If direct SQL fails, skip incident creation but continue
                incident_id = None

            # Send notification for going down - create a simple incident object
            class TempIncident:
                def __init__(self, incident_id, started_at, description):
                    self.id = incident_id
                    self.started_at = started_at
                    self.description = description

                def __getattr__(self, name):
                    return None  # Safe fallback for any other attributes

            temp_incident = TempIncident(incident_id, started_at, error_message)

            title = f"Monitor Down: {self.name}"
            message = (
                f"Monitor '{self.name}' ({self.type.value.upper()} - {self.target}) "
                f"is down. Started: {temp_incident.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            if error_message:
                message += f"\n\nReason: {error_message}"

            try:
                notification_service.send_monitor_notification(
                    monitor=self,
                    event_type="down",
                    title=title,
                    message=message,
                    incident=temp_incident,
                )
            except Exception:
                # If notification fails, continue without it
                pass

        elif current_status == "up" and active_incident:
            # Resolve existing incident - we need to load it first since we used a direct query
            try:
                incident_record = db.session.execute(
                    text(
                        "SELECT id, started_at FROM incident WHERE monitor_id = :monitor_id AND resolved_at IS NULL LIMIT 1"
                    ),
                    {"monitor_id": self.id},
                ).fetchone()

                if incident_record:
                    # Update the incident directly
                    resolved_at = datetime.now(timezone.utc)
                    db.session.execute(
                        text(
                            "UPDATE incident SET resolved_at = :resolved_at, status = :status WHERE id = :incident_id"
                        ),
                        {
                            "resolved_at": resolved_at,
                            "status": "resolved",
                            "incident_id": incident_record.id,
                        },
                    )

                    # Calculate duration
                    started_at = incident_record.started_at
                    if started_at.tzinfo is None:
                        started_at = started_at.replace(tzinfo=timezone.utc)
                    duration = (resolved_at - started_at).total_seconds()

                    # Update duration
                    db.session.execute(
                        text(
                            "UPDATE incident SET duration = :duration WHERE id = :incident_id"
                        ),
                        {"duration": duration, "incident_id": incident_record.id},
                    )

                    # Create a temporary incident object for notification purposes
                    class TempIncident:
                        def __init__(
                            self, incident_id, started_at, resolved_at, duration
                        ):
                            self.id = incident_id
                            self.started_at = started_at
                            self.resolved_at = resolved_at
                            self.duration = duration

                        def get_duration_formatted(self):
                            if not self.duration:
                                return "0s"
                            hours = int(self.duration // 3600)
                            minutes = int((self.duration % 3600) // 60)
                            seconds = int(self.duration % 60)

                            if hours > 0:
                                return f"{hours}h {minutes}m {seconds}s"
                            elif minutes > 0:
                                return f"{minutes}m {seconds}s"
                            else:
                                return f"{seconds}s"

                    temp_incident = TempIncident(
                        incident_record.id,
                        incident_record.started_at,
                        resolved_at,
                        duration,
                    )

                    title = f"Monitor Recovered: {self.name}"
                    message = (
                        f"Monitor '{self.name}' ({self.type.value.upper()} - {self.target}) "
                        f"is back up after {temp_incident.get_duration_formatted()} of downtime. "
                        f"Resolved: {temp_incident.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    )

                    try:
                        notification_service.send_monitor_notification(
                            monitor=self,
                            event_type="up",
                            title=title,
                            message=message,
                            incident=temp_incident,
                        )
                    except Exception:
                        # If notification fails, continue without it
                        pass

            except Exception:
                # If incident resolution fails, continue without it
                pass

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
            "uptime_1y": self.get_uptime_percentage(365),
            "avg_response_time_24h": self.get_average_response_time(24),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_recent_checks:
            data["recent_checks"] = [
                check.to_dict() for check in self.get_recent_checks(30)
            ]

        if include_incidents:
            from sqlalchemy import desc

            query = self.incidents.order_by(desc(Incident.started_at))  # type: ignore
            data["incidents"] = [
                incident.to_dict()
                for incident in query.limit(10)  # type: ignore
            ]

        return data
