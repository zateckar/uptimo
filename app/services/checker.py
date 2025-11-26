import requests
import socket
import ssl
import time
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Any, Dict, Optional

# Optional imports
try:
    import ping3
except ImportError:
    ping3 = None

try:
    import dns.resolver

    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False
    dns = None  # type: ignore

try:
    import whois

    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False

# Optional Kafka imports
try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    KafkaProducer = None
    KafkaConsumer = None
    KafkaError = Exception


class CheckResultData:
    """Data class for check results (not to be confused with CheckResult model)."""

    def __init__(
        self,
        status: str = "unknown",
        response_time: Optional[float] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ):
        self.status = status  # 'up', 'down', 'unknown'
        self.response_time = response_time  # in milliseconds
        self.status_code = status_code
        self.error_message = error_message
        self.additional_data = additional_data or {}


class MonitorChecker:
    """Base class for all monitor checkers."""

    def __init__(self, monitor: Any) -> None:
        self.monitor = monitor

    def check(self) -> CheckResultData:
        """Perform the check and return CheckResultData."""
        raise NotImplementedError("Subclasses must implement check method")

    def _measure_response_time(self, func):
        """Measure response time of a function."""
        start_time = time.time()
        try:
            result = func()
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            return result, response_time
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            raise e

    def _check_domain_match(self, hostname: str) -> bool:
        """Check if domain matches expected domain."""
        if not self.monitor.check_domain or not self.monitor.expected_domain:
            return True

        return hostname.lower() == self.monitor.expected_domain.lower()

    def _get_domain_info(self, hostname: str) -> Dict[str, Any]:
        """Get domain registration information."""
        if not WHOIS_AVAILABLE:
            return {"error": "whois library not available"}

        try:
            domain_info = whois.whois(hostname)

            # Parse dates to ensure they're serializable
            creation_date = domain_info.creation_date
            expiration_date = domain_info.expiration_date
            updated_date = domain_info.updated_date

            # Handle lists (some whois returns lists)
            if isinstance(creation_date, list):
                creation_date = creation_date[0] if creation_date else None
            if isinstance(expiration_date, list):
                expiration_date = expiration_date[0] if expiration_date else None
            if isinstance(updated_date, list):
                updated_date = updated_date[0] if updated_date else None

            # Calculate days to expiration
            days_to_expiration = None
            if expiration_date:
                if expiration_date.tzinfo is None:
                    expiration_date = expiration_date.replace(tzinfo=timezone.utc)
                days_to_expiration = (expiration_date - datetime.now(timezone.utc)).days

            return {
                "domain": hostname,
                "registrar": domain_info.registrar,
                "creation_date": creation_date.isoformat() if creation_date else None,
                "expiration_date": expiration_date.isoformat()
                if expiration_date
                else None,
                "updated_date": updated_date.isoformat() if updated_date else None,
                "days_to_expiration": days_to_expiration,
                "name_servers": domain_info.name_servers,
                "status": domain_info.status,
                "registrant": domain_info.registrant,
                "admin_email": domain_info.admin_emails,
                "tech_email": domain_info.tech_emails,
            }
        except Exception as e:
            return {"error": str(e), "domain": hostname}

    def _get_dns_info(self, hostname: str) -> Dict[str, Any]:
        """Get DNS information for the hostname."""
        if not DNS_AVAILABLE:
            return {"error": "dns library not available"}

        try:
            dns_info = {}

            # Get A records
            try:
                a_records = dns.resolver.resolve(hostname, "A")
                dns_info["a_records"] = [str(record) for record in a_records]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                dns_info["a_records"] = []

            # Get AAAA records (IPv6)
            try:
                aaaa_records = dns.resolver.resolve(hostname, "AAAA")
                dns_info["aaaa_records"] = [str(record) for record in aaaa_records]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                dns_info["aaaa_records"] = []

            # Get MX records
            try:
                mx_records = dns.resolver.resolve(hostname, "MX")
                dns_info["mx_records"] = [
                    f"{record.exchange} ({record.preference})" for record in mx_records
                ]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                dns_info["mx_records"] = []

            # Get NS records
            try:
                ns_records = dns.resolver.resolve(hostname, "NS")
                dns_info["ns_records"] = [str(record) for record in ns_records]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                dns_info["ns_records"] = []

            # Get TXT records
            try:
                txt_records = dns.resolver.resolve(hostname, "TXT")
                dns_info["txt_records"] = [str(record) for record in txt_records]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                dns_info["txt_records"] = []

            return dns_info
        except Exception as e:
            return {"error": str(e), "hostname": hostname}


class HTTPChecker(MonitorChecker):
    """Checker for HTTP/HTTPS endpoints."""

    def check(self) -> CheckResultData:
        url = self.monitor.target
        if not url.startswith(("http://", "https://")):
            if self.monitor.type.value == "https":
                url = f"https://{url}"
            else:
                url = f"http://{url}"

        headers = {"User-Agent": "Uptimo-Monitor/1.0"}

        # Add custom headers if provided
        if self.monitor.http_headers:
            try:
                custom_headers = json.loads(self.monitor.http_headers)
                headers.update(custom_headers)
            except json.JSONDecodeError:
                pass  # Ignore invalid JSON headers

        parsed_url = urlparse(url)

        try:
            # Prepare request parameters
            request_kwargs = {
                "headers": headers,
                "timeout": self.monitor.timeout,
                "allow_redirects": True,
            }

            # Handle SSL/TLS settings
            if url.startswith("https://"):
                request_kwargs["verify"] = self.monitor.verify_ssl

                # Add mTLS certificates if provided
                if (
                    self.monitor.http_ssl_client_cert
                    and self.monitor.http_ssl_client_key
                ):
                    import tempfile

                    # Create temporary files for certificates
                    cert_file = tempfile.NamedTemporaryFile(
                        mode="w", delete=False, suffix=".pem"
                    )
                    cert_file.write(self.monitor.http_ssl_client_cert)
                    cert_file.close()

                    key_file = tempfile.NamedTemporaryFile(
                        mode="w", delete=False, suffix=".pem"
                    )
                    key_file.write(self.monitor.http_ssl_client_key)
                    key_file.close()

                    request_kwargs["cert"] = (cert_file.name, key_file.name)

                    # Add CA certificate if provided
                    if self.monitor.http_ssl_ca_cert:
                        ca_file = tempfile.NamedTemporaryFile(
                            mode="w", delete=False, suffix=".pem"
                        )
                        ca_file.write(self.monitor.http_ssl_ca_cert)
                        ca_file.close()
                        request_kwargs["verify"] = ca_file.name

            # Add request body for POST/PUT/PATCH
            http_method = (self.monitor.http_method or "GET").upper()
            if http_method in ["POST", "PUT", "PATCH"] and self.monitor.http_body:
                request_kwargs["data"] = self.monitor.http_body
                # Set content-type if not already set
                if "Content-Type" not in headers and "content-type" not in headers:
                    try:
                        json.loads(self.monitor.http_body)
                        headers["Content-Type"] = "application/json"
                    except json.JSONDecodeError:
                        headers["Content-Type"] = "text/plain"

            # Perform the request based on HTTP method
            response, response_time = self._measure_response_time(
                lambda: requests.request(http_method, url, **request_kwargs)
            )

            # Check domain if required
            if self.monitor.check_domain and parsed_url.hostname:
                if not self._check_domain_match(parsed_url.hostname):
                    return CheckResultData(
                        status="down",
                        response_time=response_time,
                        error_message=f"Domain mismatch: expected {self.monitor.expected_domain}, got {parsed_url.hostname}",
                    )

            # Collect additional information
            additional_data = {}

            # Get domain and DNS information if hostname is available
            if parsed_url.hostname:
                # Get domain registration info
                domain_info = self._get_domain_info(parsed_url.hostname)
                additional_data["domain_info"] = domain_info

                # Get DNS info
                dns_info = self._get_dns_info(parsed_url.hostname)
                additional_data["dns_info"] = dns_info

            # Check SSL certificate if HTTPS
            if (
                url.startswith("https://")
                and self.monitor.check_cert_expiration
                and parsed_url.hostname
            ):
                cert_info = self._check_ssl_certificate(
                    parsed_url.hostname, parsed_url.port or 443
                )
                additional_data["ssl_info"] = cert_info

                # Check certificate expiration
                if (
                    cert_info.get("days_to_expiration", 999)
                    <= self.monitor.cert_expiration_threshold
                ):
                    # Send SSL warning notification but continue check
                    self._send_ssl_warning(cert_info, response_time)

                    return CheckResultData(
                        status="down",
                        response_time=response_time,
                        status_code=response.status_code,
                        error_message=f"SSL certificate expires in {cert_info['days_to_expiration']} days",
                        additional_data=additional_data,
                    )

            # Check status code
            if self.monitor.expected_status_codes:
                try:
                    expected_codes = json.loads(self.monitor.expected_status_codes)
                    if response.status_code not in expected_codes:
                        return CheckResultData(
                            status="down",
                            response_time=response_time,
                            status_code=response.status_code,
                            error_message=f"Unexpected status code: {response.status_code}",
                            additional_data=additional_data,
                        )
                except json.JSONDecodeError:
                    # Default to 200 if JSON parsing fails
                    if response.status_code != 200:
                        return CheckResultData(
                            status="down",
                            response_time=response_time,
                            status_code=response.status_code,
                            error_message=f"Unexpected status code: {response.status_code}",
                            additional_data=additional_data,
                        )

            # Check response time threshold
            if (
                self.monitor.response_time_threshold
                and response_time > self.monitor.response_time_threshold
            ):
                return CheckResultData(
                    status="down",
                    response_time=response_time,
                    status_code=response.status_code,
                    error_message=f"Response time {response_time:.2f}ms exceeds threshold {self.monitor.response_time_threshold}ms",
                    additional_data=additional_data,
                )

            # Check string matching
            if self.monitor.string_match:
                content = response.text
                if self.monitor.string_match_type == "contains":
                    if self.monitor.string_match not in content:
                        return CheckResultData(
                            status="down",
                            response_time=response_time,
                            status_code=response.status_code,
                            error_message=f'String "{self.monitor.string_match}" not found in response',
                            additional_data=additional_data,
                        )
                elif self.monitor.string_match_type == "not_contains":
                    if self.monitor.string_match in content:
                        return CheckResultData(
                            status="down",
                            response_time=response_time,
                            status_code=response.status_code,
                            error_message=f'String "{self.monitor.string_match}" found in response (should not be present)',
                            additional_data=additional_data,
                        )
                elif self.monitor.string_match_type == "regex":
                    try:
                        if not re.search(self.monitor.string_match, content):
                            return CheckResultData(
                                status="down",
                                response_time=response_time,
                                status_code=response.status_code,
                                error_message=f'Regex pattern "{self.monitor.string_match}" not found in response',
                                additional_data=additional_data,
                            )
                    except re.error as e:
                        return CheckResultData(
                            status="down",
                            response_time=response_time,
                            status_code=response.status_code,
                            error_message=f"Invalid regex pattern: {str(e)}",
                            additional_data=additional_data,
                        )

            return CheckResultData(
                status="up",
                response_time=response_time,
                status_code=response.status_code,
                additional_data=additional_data,
            )

        except requests.exceptions.Timeout:
            return CheckResultData(
                status="down",
                error_message=f"Request timeout after {self.monitor.timeout} seconds",
            )
        except requests.exceptions.ConnectionError as e:
            return CheckResultData(
                status="down", error_message=f"Connection error: {str(e)}"
            )
        except requests.exceptions.SSLError as e:
            return CheckResultData(status="down", error_message=f"SSL error: {str(e)}")
        except Exception as e:
            return CheckResultData(
                status="down", error_message=f"Unexpected error: {str(e)}"
            )

    def _check_ssl_certificate(self, hostname: str, port: int = 443) -> Dict[str, Any]:
        """Check SSL certificate information."""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

                    if not cert:
                        return {
                            "error": "No certificate found",
                            "days_to_expiration": 0,
                        }

                    # Get expiration date
                    expire_date_str = cert.get("notAfter")
                    if not expire_date_str:
                        return {
                            "error": "No expiration date found",
                            "days_to_expiration": 0,
                        }

                    if not isinstance(expire_date_str, str):
                        return {
                            "error": "Invalid expiration date format",
                            "days_to_expiration": 0,
                        }

                    expire_date = datetime.strptime(
                        expire_date_str, "%b %d %H:%M:%S %Y %Z"
                    )
                    # Make expire_date timezone-aware (assuming UTC for SSL cert dates)
                    expire_date = expire_date.replace(tzinfo=timezone.utc)
                    days_to_expiration = (expire_date - datetime.now(timezone.utc)).days

                    # Extract certificate subject and issuer information
                    subject_dict = {}
                    for item in cert.get("subject", []):
                        if len(item) >= 1 and len(item[0]) >= 2:
                            subject_dict[item[0][0]] = item[0][1]

                    issuer_dict = {}
                    for item in cert.get("issuer", []):
                        if len(item) >= 1 and len(item[0]) >= 2:
                            issuer_dict[item[0][0]] = item[0][1]

                    # Extract SAN names
                    san_names = []
                    for item in cert.get("subjectAltName", []):
                        if len(item) >= 2:
                            san_names.append(item[1])

                    return {
                        "subject": subject_dict,
                        "subject_raw": cert.get("subject", []),
                        "issuer": issuer_dict,
                        "issuer_raw": cert.get("issuer", []),
                        "version": cert.get("version"),
                        "serial_number": cert.get("serialNumber"),
                        "not_before": cert.get("notBefore"),
                        "not_after": cert.get("notAfter"),
                        "days_to_expiration": days_to_expiration,
                        "subject_alt_name": san_names,
                        "subject_alt_name_raw": cert.get("subjectAltName", []),
                        "signature_algorithm": cert.get("signatureAlgorithm"),
                        "public_key_algorithm": cert.get("pubkeyAlg"),
                    }
        except Exception as e:
            return {"error": str(e), "days_to_expiration": 0}

    def _send_ssl_warning(
        self, cert_info: Dict[str, Any], response_time: float
    ) -> None:
        """Send SSL certificate expiration warning notification."""
        from app.notification.service import notification_service

        days_to_expiration = cert_info.get("days_to_expiration", 0)
        hostname = cert_info.get("subject", {}).get("commonName", "unknown")

        title = f"SSL Certificate Expiring Soon: {hostname}"
        message = (
            f"SSL certificate for {hostname} expires in {days_to_expiration} days. "
            f"Monitor: {self.monitor.name} ({self.monitor.target}). "
            f"Current response time: {response_time:.2f}ms"
        )

        notification_service.send_monitor_notification(
            monitor=self.monitor,
            event_type="ssl_warning",
            title=title,
            message=message,
        )


class TCPChecker(MonitorChecker):
    """Checker for TCP port connectivity."""

    def check(self) -> CheckResultData:
        try:

            def connect():
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.monitor.timeout)
                result = sock.connect_ex((self.monitor.target, self.monitor.port))
                sock.close()
                return result

            exit_code, response_time = self._measure_response_time(connect)

            additional_data = {}

            # Get DNS info for TCP targets if it's a hostname
            if (
                self.monitor.check_domain
                and not self.monitor.target.replace(".", "").replace("-", "").isdigit()
            ):
                dns_info = self._get_dns_info(self.monitor.target)
                additional_data["dns_info"] = dns_info

            if exit_code == 0:
                return CheckResultData(
                    status="up",
                    response_time=response_time,
                    additional_data=additional_data,
                )
            else:
                return CheckResultData(
                    status="down",
                    response_time=response_time,
                    error_message=f"Connection failed to {self.monitor.target}:{self.monitor.port}",
                    additional_data=additional_data,
                )

        except Exception as e:
            return CheckResultData(
                status="down", error_message=f"TCP check failed: {str(e)}"
            )


class PingChecker(MonitorChecker):
    """Checker for ICMP ping."""

    def check(self) -> CheckResultData:
        if not ping3:
            return CheckResultData(
                status="down",
                error_message="ping3 library not available. Install ping3 package.",
            )

        try:
            additional_data = {}

            # Get DNS info for ping targets if it's a hostname
            if (
                self.monitor.check_domain
                and not self.monitor.target.replace(".", "").replace("-", "").isdigit()
            ):
                dns_info = self._get_dns_info(self.monitor.target)
                additional_data["dns_info"] = dns_info

            response_time = ping3.ping(
                self.monitor.target, timeout=self.monitor.timeout
            )

            if response_time is not None:
                return CheckResultData(
                    status="up",
                    response_time=response_time * 1000,  # Convert to milliseconds
                    additional_data=additional_data,
                )
            else:
                return CheckResultData(
                    status="down",
                    error_message=f"Ping failed to {self.monitor.target}",
                    additional_data=additional_data,
                )

        except Exception as e:
            return CheckResultData(
                status="down", error_message=f"Ping check failed: {str(e)}"
            )


class KafkaChecker(MonitorChecker):
    """Checker for Kafka broker connectivity with advanced features."""

    def check(self) -> CheckResultData:
        if not KAFKA_AVAILABLE or not KafkaProducer:
            return CheckResultData(
                status="down",
                error_message="Kafka library not available. Install kafka-python package.",
            )

        try:
            bootstrap_servers = self.monitor.target.split(",")
            kafka_config = self._build_kafka_config(bootstrap_servers)

            def test_kafka_connection():
                additional_data: Dict[str, Any] = {}

                # Test basic connectivity
                producer = KafkaProducer(**kafka_config)
                producer.bootstrap_connected()
                producer.close()

                # Get cluster metadata
                try:
                    from kafka.admin import KafkaAdminClient

                    admin_config = {
                        k: v for k, v in kafka_config.items() if k != "value_serializer"
                    }
                    admin_client = KafkaAdminClient(**admin_config)
                    cluster_metadata = admin_client.describe_cluster()
                    admin_client.close()

                    additional_data["brokers"] = len(
                        cluster_metadata.get("brokers", [])
                    )
                    additional_data["cluster_id"] = cluster_metadata.get(
                        "cluster_id", "unknown"
                    )
                except Exception as e:
                    additional_data["brokers"] = 0
                    additional_data["cluster_id"] = "unknown"
                    additional_data["metadata_error"] = str(e)

                # Check SSL certificate if using SSL
                if self.monitor.kafka_security_protocol in ["SSL", "SASL_SSL"]:
                    cert_info = self._check_kafka_ssl_certificate(bootstrap_servers[0])
                    additional_data["ssl_info"] = cert_info

                # Read message if requested
                if self.monitor.kafka_read_message and self.monitor.kafka_topic:
                    message_data = self._read_latest_message(kafka_config)
                    additional_data["message_read"] = message_data

                # Write message if requested
                if self.monitor.kafka_write_message and self.monitor.kafka_topic:
                    write_result = self._write_message(kafka_config)
                    additional_data["message_write"] = write_result

                return additional_data

            additional_data, response_time = self._measure_response_time(
                test_kafka_connection
            )

            return CheckResultData(
                status="up",
                response_time=response_time,
                additional_data=additional_data,
            )

        except KafkaError as e:
            return CheckResultData(
                status="down", error_message=f"Kafka connection error: {str(e)}"
            )
        except Exception as e:
            return CheckResultData(
                status="down", error_message=f"Kafka check failed: {str(e)}"
            )

    def _build_kafka_config(self, bootstrap_servers: list) -> Dict[str, Any]:
        """Build Kafka configuration from monitor settings."""
        config: Dict[str, Any] = {
            "bootstrap_servers": bootstrap_servers,
            "security_protocol": self.monitor.kafka_security_protocol or "PLAINTEXT",
            "request_timeout_ms": self.monitor.timeout * 1000,
        }

        # Add SASL configuration
        if self.monitor.kafka_sasl_mechanism:
            config["sasl_mechanism"] = self.monitor.kafka_sasl_mechanism

            if self.monitor.kafka_sasl_mechanism in [
                "PLAIN",
                "SCRAM-SHA-256",
                "SCRAM-SHA-512",
            ]:
                config["sasl_plain_username"] = self.monitor.kafka_sasl_username
                config["sasl_plain_password"] = self.monitor.kafka_sasl_password

            elif self.monitor.kafka_sasl_mechanism == "OAUTHBEARER":
                # OAuth token will be fetched and set
                token = self._get_oauth_token()
                if token:
                    config["sasl_oauth_token_provider"] = lambda: token

        # Add SSL configuration
        if self.monitor.kafka_security_protocol in ["SSL", "SASL_SSL"]:
            import tempfile

            # Write certificates to temporary files
            if self.monitor.kafka_ssl_ca_cert:
                ca_cert_file = tempfile.NamedTemporaryFile(
                    mode="w", delete=False, suffix=".pem"
                )
                ca_cert_file.write(self.monitor.kafka_ssl_ca_cert)
                ca_cert_file.close()
                config["ssl_cafile"] = ca_cert_file.name

            if self.monitor.kafka_ssl_client_cert:
                client_cert_file = tempfile.NamedTemporaryFile(
                    mode="w", delete=False, suffix=".pem"
                )
                client_cert_file.write(self.monitor.kafka_ssl_client_cert)
                client_cert_file.close()
                config["ssl_certfile"] = client_cert_file.name

            if self.monitor.kafka_ssl_client_key:
                client_key_file = tempfile.NamedTemporaryFile(
                    mode="w", delete=False, suffix=".pem"
                )
                client_key_file.write(self.monitor.kafka_ssl_client_key)
                client_key_file.close()
                config["ssl_keyfile"] = client_key_file.name

            config["ssl_check_hostname"] = True

        # Add serializer for producer
        config["value_serializer"] = lambda v: json.dumps(v).encode("utf-8")

        return config

    def _get_oauth_token(self) -> Optional[str]:
        """Fetch OAuth token using client credentials flow."""
        if not all(
            [
                self.monitor.kafka_oauth_token_url,
                self.monitor.kafka_oauth_client_id,
                self.monitor.kafka_oauth_client_secret,
            ]
        ):
            return None

        try:
            response = requests.post(
                self.monitor.kafka_oauth_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.monitor.kafka_oauth_client_id,
                    "client_secret": self.monitor.kafka_oauth_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.monitor.timeout,
            )
            response.raise_for_status()
            token_data = response.json()
            return token_data.get("access_token")
        except Exception:
            return None

    def _read_latest_message(self, kafka_config: Dict[str, Any]) -> Dict[str, Any]:
        """Read the latest message from the configured topic."""
        try:
            consumer_config = {
                k: v for k, v in kafka_config.items() if k != "value_serializer"
            }
            consumer_config["auto_offset_reset"] = "latest"
            consumer_config["enable_auto_commit"] = self.monitor.kafka_autocommit
            consumer_config["consumer_timeout_ms"] = 5000
            consumer_config["value_deserializer"] = lambda v: v.decode("utf-8")

            consumer = KafkaConsumer(self.monitor.kafka_topic, **consumer_config)

            # Read one message
            message = None
            for msg in consumer:
                message = msg
                break

            consumer.close()

            if message:
                return {
                    "success": True,
                    "topic": message.topic,
                    "partition": message.partition,
                    "offset": message.offset,
                    "timestamp": message.timestamp,
                    "value": message.value[:500],  # Limit to 500 chars
                }
            else:
                return {"success": False, "error": "No messages available"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _write_message(self, kafka_config: Dict[str, Any]) -> Dict[str, Any]:
        """Write a test message to the configured topic."""
        try:
            producer = KafkaProducer(**kafka_config)

            # Parse the message payload
            if self.monitor.kafka_message_payload:
                payload = json.loads(self.monitor.kafka_message_payload)
            else:
                payload = {"test": "message", "timestamp": time.time()}

            # Send the message
            future = producer.send(self.monitor.kafka_topic, payload)
            record_metadata = future.get(timeout=self.monitor.timeout)

            producer.close()

            return {
                "success": True,
                "topic": record_metadata.topic,
                "partition": record_metadata.partition,
                "offset": record_metadata.offset,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _check_kafka_ssl_certificate(self, broker: str) -> Dict[str, Any]:
        """Check SSL certificate for Kafka broker."""
        try:
            # Parse broker address
            if ":" in broker:
                host, port_str = broker.rsplit(":", 1)
                port = int(port_str)
            else:
                host = broker
                port = 9093  # Default Kafka SSL port

            # Get certificate info
            context = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()

                    if not cert:
                        return {
                            "error": "No certificate found",
                            "days_to_expiration": 0,
                        }

                    expire_date_str = cert.get("notAfter")
                    if not expire_date_str or not isinstance(expire_date_str, str):
                        return {
                            "error": "No expiration date found",
                            "days_to_expiration": 0,
                        }

                    expire_date = datetime.strptime(
                        expire_date_str, "%b %d %H:%M:%S %Y %Z"
                    )
                    expire_date = expire_date.replace(tzinfo=timezone.utc)
                    days_to_expiration = (expire_date - datetime.now(timezone.utc)).days

                    subject_dict = {}
                    for item in cert.get("subject", []):
                        if len(item) >= 1 and len(item[0]) >= 2:
                            subject_dict[item[0][0]] = item[0][1]

                    return {
                        "subject": subject_dict,
                        "not_after": cert.get("notAfter"),
                        "days_to_expiration": days_to_expiration,
                    }

        except Exception as e:
            return {"error": str(e), "days_to_expiration": 0}


class CheckerFactory:
    """Factory for creating appropriate checker instances."""

    @staticmethod
    def create_checker(monitor):
        """Create appropriate checker based on monitor type."""
        from app.models.monitor import MonitorType

        if monitor.type in [MonitorType.HTTP, MonitorType.HTTPS]:
            return HTTPChecker(monitor)
        elif monitor.type == MonitorType.TCP:
            return TCPChecker(monitor)
        elif monitor.type == MonitorType.PING:
            return PingChecker(monitor)
        elif monitor.type == MonitorType.KAFKA:
            return KafkaChecker(monitor)
        else:
            raise ValueError(f"Unsupported monitor type: {monitor.type}")
