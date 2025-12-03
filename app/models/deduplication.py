"""Deduplication reference table models."""

import json
from datetime import datetime, timezone
from typing import Any, Dict

from app import db


class ErrorMessage(db.Model):
    """Deduplicated error messages."""

    __tablename__ = "error_messages"

    id = db.Column(db.Integer, primary_key=True)
    message_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    usage_count = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Indexes
    __table_args__ = (
        db.Index("idx_error_message_hash", "message_hash"),
        db.Index("idx_error_message_usage", "usage_count"),
    )

    def __repr__(self) -> str:
        return f"<ErrorMessage {self.id} ({self.usage_count} uses)>"


class TLSCertificate(db.Model):
    """Deduplicated TLS certificates."""

    __tablename__ = "tls_certificates"

    id = db.Column(db.Integer, primary_key=True)
    cert_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    domain = db.Column(db.String(500), nullable=False, index=True)
    cert_data = db.Column(db.Text, nullable=False)  # JSON with full cert info
    expires_at = db.Column(db.DateTime, index=True)
    usage_count = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Indexes
    __table_args__ = (
        db.Index("idx_tls_cert_hash", "cert_hash"),
        db.Index("idx_tls_cert_domain", "domain"),
        db.Index("idx_tls_cert_expires", "expires_at"),
        db.Index("idx_tls_cert_usage", "usage_count"),
    )

    def get_cert_data(self) -> Dict[str, Any]:
        """Parse and return certificate data as dict with updated expiration."""
        try:
            cert_data = json.loads(self.cert_data)

            # If expires_at is None, try to parse it from cert_data
            if not self.expires_at and cert_data.get("not_after"):
                try:
                    not_after = cert_data["not_after"]
                    # Parse SSL cert date (format: "Jan 9 12:31:51 2026 GMT")
                    # Remove timezone suffix as strptime %Z is unreliable
                    expire_date_clean = not_after.rsplit(" ", 1)[0]
                    expires_at = datetime.strptime(
                        expire_date_clean, "%b %d %H:%M:%S %Y"
                    )
                    # SSL certs are always in UTC/GMT
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                    # Update the stored value for future use
                    self.expires_at = expires_at
                except (ValueError, AttributeError):
                    pass

            # Ensure not_after field exists if we have expires_at
            if self.expires_at and not cert_data.get("not_after"):
                # Reconstruct not_after from expires_at in SSL cert format
                cert_data["not_after"] = self.expires_at.strftime(
                    "%b %d %H:%M:%S %Y GMT"
                )

            # Recalculate days_to_expiration based on current time
            if self.expires_at:
                # Ensure expires_at is timezone-aware for comparison
                expires_at_aware = self.expires_at
                if expires_at_aware.tzinfo is None:
                    # Database datetime is naive, treat as UTC
                    expires_at_aware = expires_at_aware.replace(tzinfo=timezone.utc)

                delta = expires_at_aware - datetime.now(timezone.utc)
                # Use total_seconds() divided by seconds per day for more precision
                cert_data["days_to_expiration"] = int(delta.total_seconds() // 86400)

            return cert_data
        except (json.JSONDecodeError, TypeError):
            return {}

    def is_expired(self) -> bool:
        """Check if certificate is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def days_until_expiry(self) -> int:
        """Get days until certificate expires."""
        if not self.expires_at:
            return -1
        delta = self.expires_at - datetime.now(timezone.utc)
        # Use total_seconds() divided by seconds per day for more precision
        return int(delta.total_seconds() // 86400)

    def __repr__(self) -> str:
        return f"<TLSCertificate {self.domain} ({self.usage_count} uses)>"


class DomainInfo(db.Model):
    """Deduplicated domain information."""

    __tablename__ = "domain_info"

    id = db.Column(db.Integer, primary_key=True)
    domain_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    domain = db.Column(db.String(500), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    dns_info = db.Column(db.Text)  # JSON with DNS details
    usage_count = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        db.Index("idx_domain_hash", "domain_hash"),
        db.Index("idx_domain_name", "domain"),
        db.Index("idx_domain_usage", "usage_count"),
    )

    def get_dns_info(self) -> Dict[str, Any]:
        """
        Parse and return domain check data as dict.

        Note: Despite the name, this returns ALL domain check data including:
        - Domain registration information (registrar, expiration dates, etc.)
        - DNS records (A, AAAA, MX, NS, TXT, etc.)

        Returns:
            Dictionary containing complete domain check data
        """
        try:
            return json.loads(self.dns_info or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def __repr__(self) -> str:
        return f"<DomainInfo {self.domain} ({self.usage_count} uses)>"
