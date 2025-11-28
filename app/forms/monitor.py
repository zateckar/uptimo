import json
import re
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    IntegerField,
    BooleanField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)
from app.models.monitor import MonitorType, CheckInterval


class MonitorForm(FlaskForm):
    """Form for creating and editing monitors"""

    # Basic Information
    name = StringField(
        "Monitor Name",
        validators=[
            DataRequired(message="Monitor name is required"),
            Length(min=1, max=200, message="Name must be between 1 and 200 characters"),
        ],
    )

    type = SelectField(
        "Monitor Type",
        choices=[
            (MonitorType.HTTP.value, "HTTP"),
            (MonitorType.HTTPS.value, "HTTPS"),
            (MonitorType.TCP.value, "TCP Port"),
            (MonitorType.PING.value, "Ping"),
            (MonitorType.KAFKA.value, "Kafka Broker"),
        ],
        validators=[DataRequired(message="Monitor type is required")],
    )

    target = StringField(
        "Target",
        validators=[
            DataRequired(message="Target is required"),
            Length(
                min=1, max=500, message="Target must be between 1 and 500 characters"
            ),
        ],
    )

    port = IntegerField(
        "Port (TCP only)",
        validators=[
            Optional(),
            NumberRange(min=1, max=65535, message="Port must be between 1 and 65535"),
        ],
    )

    # Check Settings
    check_interval = SelectField(
        "Check Interval",
        choices=[
            (CheckInterval.THIRTY_SECONDS.value, "30 seconds"),
            (CheckInterval.ONE_MINUTE.value, "1 minute"),
            (CheckInterval.FIVE_MINUTES.value, "5 minutes"),
            (CheckInterval.FIFTEEN_MINUTES.value, "15 minutes"),
            (CheckInterval.THIRTY_MINUTES.value, "30 minutes"),
            (CheckInterval.ONE_HOUR.value, "1 hour"),
        ],
        coerce=int,
        validators=[DataRequired(message="Check interval is required")],
    )

    timeout = IntegerField(
        "Timeout (seconds)",
        validators=[
            DataRequired(message="Timeout is required"),
            NumberRange(
                min=1, max=300, message="Timeout must be between 1 and 300 seconds"
            ),
        ],
        default=30,
    )

    # HTTP-specific settings
    http_method = SelectField(
        "HTTP Method",
        choices=[
            ("GET", "GET"),
            ("POST", "POST"),
            ("PUT", "PUT"),
            ("PATCH", "PATCH"),
            ("HEAD", "HEAD"),
        ],
        default="GET",
    )

    http_headers = TextAreaField(
        "Custom HTTP Headers (JSON)",
        validators=[Optional()],
        description='JSON object with custom headers (e.g., {"Authorization": "Bearer token"})',
    )

    http_body = TextAreaField(
        "Request Body",
        validators=[Optional()],
        description="Request body for POST/PUT/PATCH requests",
    )

    expected_status_codes = TextAreaField(
        "Expected Status Codes",
        description="Enter comma-separated status codes (e.g., 200, 201, 202)",
    )

    response_time_threshold = IntegerField(
        "Response Time Threshold (ms)",
        validators=[
            Optional(),
            NumberRange(
                min=1,
                max=300000,
                message="Response time threshold must be between 1 and 300000 ms",
            ),
        ],
    )

    string_match = StringField(
        "String Match",
        validators=[
            Optional(),
            Length(max=500, message="String match must be less than 500 characters"),
        ],
        description="Text to search for in response body",
    )

    string_match_type = SelectField(
        "String Match Type",
        choices=[
            ("contains", "Contains"),
            ("not_contains", "Does Not Contain"),
            ("regex", "Regular Expression"),
        ],
        default="contains",
    )

    json_path_match = StringField(
        "JSON Path Match",
        validators=[
            Optional(),
            Length(max=500, message="JSON path match must be less than 500 characters"),
        ],
        description="JSON path expression and expected value (e.g., $.status=active)",
    )

    # TLS/SSL Settings
    verify_ssl = BooleanField("Verify SSL Certificate", default=True)
    check_cert_expiration = BooleanField("Check Certificate Expiration", default=True)
    cert_expiration_threshold = IntegerField(
        "Certificate Expiration Warning (days)",
        validators=[
            Optional(),
            NumberRange(
                min=1,
                max=365,
                message="Expiration threshold must be between 1 and 365 days",
            ),
        ],
        default=30,
    )

    # mTLS Settings for HTTPS
    http_ssl_ca_cert = TextAreaField(
        "HTTPS CA Certificate",
        validators=[Optional()],
        description="PEM-encoded CA certificate for HTTPS client authentication",
    )

    http_ssl_client_cert = TextAreaField(
        "HTTPS Client Certificate",
        validators=[Optional()],
        description="PEM-encoded client certificate for mTLS",
    )

    http_ssl_client_key = TextAreaField(
        "HTTPS Client Private Key",
        validators=[Optional()],
        description="PEM-encoded client private key for mTLS",
    )

    # Domain Settings
    check_domain = BooleanField("Check Domain", default=False)
    expected_domain = StringField(
        "Expected Domain",
        validators=[
            Optional(),
            Length(max=500, message="Expected domain must be less than 500 characters"),
        ],
    )

    # Kafka-specific settings
    kafka_security_protocol = SelectField(
        "Security Protocol",
        choices=[
            ("PLAINTEXT", "PLAINTEXT"),
            ("SSL", "SSL (mTLS)"),
            ("SASL_SSL", "SASL_SSL"),
            ("SASL_PLAINTEXT", "SASL_PLAINTEXT"),
        ],
        default="PLAINTEXT",
    )

    kafka_sasl_mechanism = SelectField(
        "SASL Mechanism",
        choices=[
            ("", "None"),
            ("PLAIN", "PLAIN"),
            ("SCRAM-SHA-256", "SCRAM-SHA-256"),
            ("SCRAM-SHA-512", "SCRAM-SHA-512"),
            ("OAUTHBEARER", "OAUTHBEARER"),
        ],
        validators=[Optional()],
    )

    kafka_sasl_username = StringField(
        "SASL Username",
        validators=[
            Optional(),
            Length(max=500, message="Username must be less than 500 characters"),
        ],
    )

    kafka_sasl_password = StringField(
        "SASL Password",
        validators=[
            Optional(),
            Length(max=500, message="Password must be less than 500 characters"),
        ],
    )

    kafka_oauth_token_url = StringField(
        "OAuth Token URL",
        validators=[
            Optional(),
            Length(max=500, message="Token URL must be less than 500 characters"),
        ],
        description="OAuth2 token endpoint for client credentials flow",
    )

    kafka_oauth_client_id = StringField(
        "OAuth Client ID",
        validators=[
            Optional(),
            Length(max=500, message="Client ID must be less than 500 characters"),
        ],
    )

    kafka_oauth_client_secret = StringField(
        "OAuth Client Secret",
        validators=[
            Optional(),
            Length(max=500, message="Client Secret must be less than 500 characters"),
        ],
    )

    kafka_ssl_ca_cert = TextAreaField(
        "SSL CA Certificate",
        validators=[Optional()],
        description="PEM-encoded CA certificate for SSL/mTLS",
    )

    kafka_ssl_client_cert = TextAreaField(
        "SSL Client Certificate",
        validators=[Optional()],
        description="PEM-encoded client certificate for mTLS",
    )

    kafka_ssl_client_key = TextAreaField(
        "SSL Client Private Key",
        validators=[Optional()],
        description="PEM-encoded client private key for mTLS",
    )

    kafka_topic = StringField(
        "Kafka Topic",
        validators=[
            Optional(),
            Length(max=500, message="Topic name must be less than 500 characters"),
        ],
        description="Topic for read/write operations",
    )

    kafka_consumer_group = StringField(
        "Consumer Group",
        validators=[
            Optional(),
            Length(max=500, message="Consumer group must be less than 500 characters"),
        ],
        description="Consumer group ID for reading messages",
    )

    kafka_read_message = BooleanField(
        "Read Latest Message", default=False, description="Read one latest message"
    )

    kafka_write_message = BooleanField(
        "Write Test Message", default=False, description="Write a test message"
    )

    kafka_message_payload = TextAreaField(
        "Message Payload (JSON)",
        validators=[Optional()],
        description="JSON payload to write to the topic",
    )

    kafka_autocommit = BooleanField(
        "Auto-commit Offset",
        default=False,
        description="Auto-commit offset when reading messages",
    )

    # Status
    is_active = BooleanField("Active Monitor", default=True)

    submit = SubmitField("Create Monitor")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default values
        if not self.check_interval.data:
            self.check_interval.data = CheckInterval.FIVE_MINUTES.value

    def get_status_codes_list(self):
        """Convert comma-separated status codes to list"""
        if self.expected_status_codes.data:
            # Split by comma and strip whitespace
            items = [
                item.strip()
                for item in self.expected_status_codes.data.split(",")
                if item.strip()
            ]
            # Convert to integers if they look like numbers
            processed_items = []
            for item in items:
                if item.isdigit():
                    processed_items.append(int(item))
                else:
                    processed_items.append(item)
            return processed_items
        return []

    def validate_target(self, target):
        """Validate target based on monitor type"""
        monitor_type = self.type.data
        target_data = target.data

        if monitor_type in [MonitorType.HTTP.value, MonitorType.HTTPS.value]:
            # Validate URL format for HTTP/HTTPS
            if not target_data.startswith(("http://", "https://")):
                raise ValidationError(
                    "Target must be a valid URL starting with http:// or https://"
                )

            # Basic URL validation
            url_pattern = re.compile(
                r"^https?://"  # http:// or https://
                r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
                r"localhost|"  # localhost...
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
                r"(?::\d+)?"  # optional port
                r"(?:/?|[/?]\S+)$",
                re.IGNORECASE,
            )

            if not url_pattern.match(target_data):
                raise ValidationError("Please enter a valid URL")

        elif monitor_type == MonitorType.TCP.value:
            # Just validate it's a hostname or IP
            if not target_data:
                raise ValidationError("Target is required for TCP checks")

        elif monitor_type == MonitorType.PING.value:
            # Validate hostname or IP
            hostname_pattern = re.compile(
                r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$|"
                r"^(?:\d{1,3}\.){3}\d{1,3}$|"
                r"^localhost$",
                re.IGNORECASE,
            )

            if not hostname_pattern.match(target_data):
                raise ValidationError("Target must be a valid hostname or IP address")

        elif monitor_type == MonitorType.KAFKA.value:
            # Validate Kafka broker format (host:port or host)
            if ":" in target_data:
                host, port = target_data.rsplit(":", 1)
                try:
                    port_num = int(port)
                    if not (1 <= port_num <= 65535):
                        raise ValidationError("Kafka port must be between 1 and 65535")
                except ValueError:
                    raise ValidationError("Invalid Kafka port format")

    def validate_port(self, port):
        """Validate port field for TCP monitors"""
        if self.type.data == MonitorType.TCP.value and not port.data:
            raise ValidationError("Port is required for TCP monitors")
        elif self.type.data != MonitorType.TCP.value and port.data:
            raise ValidationError("Port should only be specified for TCP monitors")

    def validate_json_path_match(self, json_path_match):
        """Validate JSON path match format"""
        if json_path_match.data:
            # Basic validation for JSON path format (should contain =)
            if "=" not in json_path_match.data:
                raise ValidationError("JSON path match must be in format: $.path=value")

    def validate_string_match_type(self, string_match_type):
        """Validate string match type consistency"""
        if self.string_match.data and not string_match_type.data:
            raise ValidationError(
                "String match type is required when string match is specified"
            )

    def validate_http_headers(self, http_headers):
        """Validate HTTP headers JSON format"""
        if http_headers.data:
            try:
                parsed = json.loads(http_headers.data)
                if not isinstance(parsed, dict):
                    raise ValidationError("HTTP headers must be a JSON object")
            except json.JSONDecodeError:
                raise ValidationError("HTTP headers must be valid JSON")

    def validate_http_ssl_client_cert(self, http_ssl_client_cert):
        """Validate mTLS client certificate"""
        if http_ssl_client_cert.data and not self.http_ssl_client_key.data:
            raise ValidationError("Client key is required with client certificate")

    def validate_expected_domain(self, expected_domain):
        """Validate expected domain field"""
        if self.check_domain.data and not expected_domain.data:
            raise ValidationError(
                "Expected domain is required when domain checking is enabled"
            )

    def validate_expected_status_codes(self, expected_status_codes):
        """Validate expected status codes for HTTP monitors"""
        monitor_type = self.type.data
        if monitor_type in [MonitorType.HTTP.value, MonitorType.HTTPS.value]:
            if not expected_status_codes.data:
                raise ValidationError(
                    "At least one expected status code is required for HTTP/HTTPS monitors"
                )
        elif expected_status_codes.data and monitor_type not in [
            MonitorType.HTTP.value,
            MonitorType.HTTPS.value,
        ]:
            raise ValidationError(
                "Expected status codes only apply to HTTP/HTTPS monitors"
            )

    def validate_kafka_sasl_mechanism(self, kafka_sasl_mechanism):
        """Validate SASL mechanism consistency"""
        if self.type.data == MonitorType.KAFKA.value:
            protocol = self.kafka_security_protocol.data
            if protocol in ["SASL_SSL", "SASL_PLAINTEXT"]:
                if not kafka_sasl_mechanism.data:
                    raise ValidationError(
                        "SASL mechanism is required for SASL security protocol"
                    )

    def validate_kafka_sasl_username(self, kafka_sasl_username):
        """Validate SASL username"""
        if self.type.data == MonitorType.KAFKA.value:
            mechanism = self.kafka_sasl_mechanism.data
            if mechanism in ["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"]:
                if not kafka_sasl_username.data:
                    raise ValidationError(
                        "Username is required for PLAIN/SCRAM SASL mechanisms"
                    )

    def validate_kafka_sasl_password(self, kafka_sasl_password):
        """Validate SASL password"""
        if self.type.data == MonitorType.KAFKA.value:
            mechanism = self.kafka_sasl_mechanism.data
            if mechanism in ["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"]:
                if not kafka_sasl_password.data:
                    raise ValidationError(
                        "Password is required for PLAIN/SCRAM SASL mechanisms"
                    )

    def validate_kafka_oauth_token_url(self, kafka_oauth_token_url):
        """Validate OAuth token URL"""
        if self.type.data == MonitorType.KAFKA.value:
            if self.kafka_sasl_mechanism.data == "OAUTHBEARER":
                if not kafka_oauth_token_url.data:
                    raise ValidationError("OAuth token URL is required for OAUTHBEARER")

    def validate_kafka_oauth_client_id(self, kafka_oauth_client_id):
        """Validate OAuth client ID"""
        if self.type.data == MonitorType.KAFKA.value:
            if self.kafka_sasl_mechanism.data == "OAUTHBEARER":
                if not kafka_oauth_client_id.data:
                    raise ValidationError("OAuth client ID is required for OAUTHBEARER")

    def validate_kafka_oauth_client_secret(self, kafka_oauth_client_secret):
        """Validate OAuth client secret"""
        if self.type.data == MonitorType.KAFKA.value:
            if self.kafka_sasl_mechanism.data == "OAUTHBEARER":
                if not kafka_oauth_client_secret.data:
                    raise ValidationError(
                        "OAuth client secret is required for OAUTHBEARER"
                    )

    def validate_kafka_ssl_client_cert(self, kafka_ssl_client_cert):
        """Validate SSL client certificate for mTLS"""
        if self.type.data == MonitorType.KAFKA.value:
            if kafka_ssl_client_cert.data and not self.kafka_ssl_client_key.data:
                raise ValidationError(
                    "SSL client key is required with client certificate"
                )

    def validate_kafka_topic(self, kafka_topic):
        """Validate Kafka topic for read/write operations"""
        if self.type.data == MonitorType.KAFKA.value:
            if self.kafka_read_message.data or self.kafka_write_message.data:
                if not kafka_topic.data:
                    raise ValidationError(
                        "Topic is required for message read/write operations"
                    )

    def validate_kafka_message_payload(self, kafka_message_payload):
        """Validate Kafka message payload"""
        if self.type.data == MonitorType.KAFKA.value:
            if self.kafka_write_message.data:
                if not kafka_message_payload.data:
                    raise ValidationError(
                        "Message payload is required when write message is enabled"
                    )
            # Validate JSON format if payload is provided
            if kafka_message_payload.data:
                try:
                    json.loads(kafka_message_payload.data)
                except json.JSONDecodeError:
                    raise ValidationError("Message payload must be valid JSON")


class MonitorEditForm(MonitorForm):
    """Form for editing existing monitors"""

    submit = SubmitField("Update Monitor")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Convert type enum to its string value
        if self.type.data and isinstance(self.type.data, MonitorType):
            self.type.data = self.type.data.value

        # Convert check_interval enum to its integer value
        if self.check_interval.data and isinstance(
            self.check_interval.data, CheckInterval
        ):
            self.check_interval.data = self.check_interval.data.value

        # Convert stored expected_status_codes back to comma-separated format
        if self.expected_status_codes.data:
            try:
                # Try to parse as JSON list first (stringified list from DB)
                import ast

                parsed = ast.literal_eval(self.expected_status_codes.data)
                if isinstance(parsed, list):
                    # Convert back to comma-separated string for the form
                    self.expected_status_codes.data = ", ".join(
                        str(code) for code in parsed
                    )
            except (ValueError, SyntaxError):
                # If it's already a comma-separated string or invalid, leave as is
                pass
