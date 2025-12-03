"""Deduplication service for CheckResult data optimization."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app import db


class DeduplicationService:
    """Service for managing deduplication of repeated data in check results."""

    @staticmethod
    def get_or_create_error_message(message: str) -> Optional[int]:
        """
        Get or create error message record, return ID.

        Args:
            message: Full error message text

        Returns:
            ID of the error message record
        """
        if not message:
            return None

        from app.models.deduplication import ErrorMessage

        # Generate hash for deduplication
        message_hash = hashlib.sha256(message.encode()).hexdigest()

        # Try to find existing
        error_msg = ErrorMessage.query.filter_by(message_hash=message_hash).first()

        if error_msg:
            # Update usage count
            error_msg.usage_count += 1
            db.session.commit()
            return error_msg.id

        # Create new record
        error_msg = ErrorMessage()
        error_msg.message_hash = message_hash
        error_msg.message = message
        error_msg.usage_count = 1
        db.session.add(error_msg)
        db.session.commit()
        return error_msg.id

    @staticmethod
    def get_or_create_tls_cert(domain: str, cert_data: Dict[str, Any]) -> Optional[int]:
        """
        Get or create TLS certificate record, return ID.

        Args:
            domain: Domain name
            cert_data: Certificate information dictionary

        Returns:
            ID of the TLS certificate record
        """
        if not cert_data:
            return None

        from app.models.deduplication import TLSCertificate

        # Create deterministic content for deduplication hash
        # Use only stable fields that identify the certificate
        hash_content = {
            "domain": domain,
            "issuer": cert_data.get("issuer", ""),
            "subject": cert_data.get("subject", ""),
            "not_before": cert_data.get("not_before"),
            "not_after": cert_data.get("not_after"),
            "serial_number": cert_data.get("serial_number", ""),
            "fingerprint": cert_data.get("fingerprint", ""),
        }

        hash_json = json.dumps(hash_content, sort_keys=True)
        cert_hash = hashlib.sha256(hash_json.encode()).hexdigest()

        # Try to find existing
        cert = TLSCertificate.query.filter_by(cert_hash=cert_hash).first()

        if cert:
            # Update usage count
            cert.usage_count += 1
            db.session.commit()
            return cert.id

        # Create new record - store FULL cert data, not just hash fields
        expires_at = None
        if cert_data.get("not_after"):
            # Parse SSL cert date (format: "Jan 9 12:31:51 2026 GMT")
            try:
                not_after = cert_data["not_after"]
                # Remove timezone suffix as strptime %Z is unreliable
                expire_date_clean = not_after.rsplit(" ", 1)[0]
                expires_at = datetime.strptime(expire_date_clean, "%b %d %H:%M:%S %Y")
                # SSL certs are always in UTC/GMT
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            except (ValueError, AttributeError):
                pass

        cert = TLSCertificate()
        cert.cert_hash = cert_hash
        cert.domain = domain
        # Store complete cert data, not just hash fields
        cert.cert_data = json.dumps(cert_data, sort_keys=True)
        cert.expires_at = expires_at
        cert.usage_count = 1
        db.session.add(cert)
        db.session.commit()
        return cert.id

    @staticmethod
    def get_or_create_domain_info(
        domain: str, domain_data: Dict[str, Any]
    ) -> Optional[int]:
        """
        Get or create domain info record, return ID.

        Args:
            domain: Domain name
            domain_data: Domain information dictionary

        Returns:
            ID of the domain info record
        """
        if not domain_data:
            return None

        from app.models.deduplication import DomainInfo

        # Domain info is unique by domain name
        domain_hash = hashlib.sha256(domain.encode()).hexdigest()

        # Try to find existing
        info = DomainInfo.query.filter_by(domain=domain).first()

        if info:
            # Update if data changed
            current_data = info.get_dns_info()
            if current_data != domain_data:
                info.dns_info = json.dumps(domain_data)
                info.ip_address = domain_data.get("ip_address")
                info.updated_at = datetime.now(timezone.utc)

            # Update usage count
            info.usage_count += 1
            db.session.commit()
            return info.id

        # Create new record
        info = DomainInfo()
        info.domain_hash = domain_hash
        info.domain = domain
        info.ip_address = domain_data.get("ip_address")
        info.dns_info = json.dumps(domain_data)
        info.usage_count = 1
        db.session.add(info)
        db.session.commit()
        return info.id

    @staticmethod
    def compact_additional_data(
        additional_data: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Extract and deduplicate large data from additional_data.

        Args:
            additional_data: Original additional data dictionary

        Returns:
            Compacted additional data as JSON string
        """
        if not additional_data:
            return None

        compacted: Dict[str, Any] = {}

        # Process TLS certificate data - store only reference ID
        if "cert_info" in additional_data:
            cert_info = additional_data["cert_info"]
            cert_id = DeduplicationService.get_or_create_tls_cert(
                cert_info.get("domain", ""), cert_info
            )
            if cert_id:
                compacted["cert_id"] = cert_id

        # Process domain check data - store only reference ID
        if "domain_check" in additional_data:
            domain_data = additional_data["domain_check"]
            domain_id = DeduplicationService.get_or_create_domain_info(
                domain_data.get("domain", ""), domain_data
            )
            if domain_id:
                compacted["domain_id"] = domain_id

        # Process response headers (can be repetitive)
        if "response_headers" in additional_data:
            headers = additional_data["response_headers"]
            # Keep only key headers
            important_headers: dict[str, str] = {}
            for key in ["server", "content-type", "content-length", "cache-control"]:
                if key in headers:
                    important_headers[key] = headers[key]
            compacted["response_headers"] = important_headers

        # Keep other small data as-is
        for key, value in additional_data.items():
            if key not in ["cert_info", "domain_check", "response_headers"]:
                compacted[key] = value

        return json.dumps(compacted, separators=(",", ":"))

    @staticmethod
    def get_error_message_text(error_message_id: Optional[int]) -> Optional[str]:
        """Get full error message text from ID."""
        if not error_message_id:
            return None

        from app.models.deduplication import ErrorMessage

        error_msg = ErrorMessage.query.get(error_message_id)
        return error_msg.message if error_msg else None

    @staticmethod
    def reconstruct_additional_data(
        additional_data_json: Optional[str],
    ) -> Dict[str, Any]:
        """
        Reconstruct full additional_data from compacted version.

        Args:
            additional_data_json: Compacted additional data JSON

        Returns:
            Reconstructed additional data dictionary
        """
        if not additional_data_json:
            return {}

        try:
            compacted = json.loads(additional_data_json)
        except (json.JSONDecodeError, TypeError):
            return {}

        reconstructed = {}

        # Reconstruct TLS certificate data
        if "cert_id" in compacted:
            from app.models.deduplication import TLSCertificate

            cert = TLSCertificate.query.get(compacted["cert_id"])
            if cert:
                reconstructed["cert_info"] = cert.get_cert_data()
                # Add runtime status if available from original data
                if "cert_valid" in compacted:
                    reconstructed["cert_info"]["valid"] = compacted["cert_valid"]

        # Reconstruct domain check data
        if "domain_id" in compacted:
            from app.models.deduplication import DomainInfo

            domain_info = DomainInfo.query.get(compacted["domain_id"])
            if domain_info:
                reconstructed["domain_check"] = domain_info.get_dns_info()
                # Add runtime status if available from original data
                if "domain_passed" in compacted:
                    reconstructed["domain_check"]["passed"] = compacted["domain_passed"]

        # Copy other data as-is
        for key, value in compacted.items():
            if key not in ["cert_id", "domain_id"]:
                reconstructed[key] = value

        return reconstructed

    @staticmethod
    def get_deduplication_stats() -> Dict[str, Any]:
        """Get statistics about deduplication effectiveness."""
        from app.models.deduplication import ErrorMessage, TLSCertificate, DomainInfo
        from app.models.check_result import CheckResult

        try:
            # Error message stats
            error_messages = ErrorMessage.query.count()
            error_uses = (
                db.session.query(db.func.sum(ErrorMessage.usage_count)).scalar() or 0
            )

            # TLS certificate stats
            tls_certs = TLSCertificate.query.count()
            tls_uses = (
                db.session.query(db.func.sum(TLSCertificate.usage_count)).scalar() or 0
            )

            # Domain info stats
            domain_infos = DomainInfo.query.count()
            domain_uses = (
                db.session.query(db.func.sum(DomainInfo.usage_count)).scalar() or 0
            )

            # Check result stats
            total_check_results = CheckResult.query.count()

            return {
                "error_messages": {
                    "unique_messages": error_messages,
                    "total_uses": error_uses,
                    "deduplication_ratio": (
                        f"{1 - (error_messages / error_uses):.2%}"
                        if error_uses > 0
                        else "0%"
                    ),
                },
                "tls_certificates": {
                    "unique_certs": tls_certs,
                    "total_uses": tls_uses,
                    "deduplication_ratio": (
                        f"{1 - (tls_certs / tls_uses):.2%}" if tls_uses > 0 else "0%"
                    ),
                },
                "domain_info": {
                    "unique_domains": domain_infos,
                    "total_uses": domain_uses,
                    "deduplication_ratio": (
                        f"{1 - (domain_infos / domain_uses):.2%}"
                        if domain_uses > 0
                        else "0%"
                    ),
                },
                "overview": {
                    "total_check_results": total_check_results,
                    "reference_records": error_messages + tls_certs + domain_infos,
                },
            }
        except Exception as e:
            return {"error": str(e)}


# Global instance
deduplication_service = DeduplicationService()
