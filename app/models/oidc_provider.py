"""OIDC Provider Configuration Model."""

from datetime import datetime, timezone
from typing import Dict

from app import db
from app.services.oidc_service import OIDCService


class OIDCProvider(db.Model):
    """OIDC Provider Configuration."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)

    # Configuration can be either issuer_url (for discovery) or explicit URLs
    issuer_url = db.Column(db.String(500), nullable=True)  # For auto-discovery
    client_id = db.Column(db.String(255), nullable=False)
    client_secret = db.Column(db.String(255), nullable=False)

    # Override URLs (optional, used if issuer_url is not set)
    auth_url = db.Column(db.String(500), nullable=True)
    token_url = db.Column(db.String(500), nullable=True)
    jwks_url = db.Column(db.String(500), nullable=True)
    userinfo_url = db.Column(db.String(500), nullable=True)

    scope = db.Column(db.String(200), nullable=False, default="openid email profile")
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def get_endpoint_data(self) -> Dict[str, str]:
        """Get endpoint data, using discovery if issuer_url is set."""
        if self.issuer_url:
            discovered = OIDCService.discover_provider(self.issuer_url)
            return {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope,
                **discovered,
            }
        else:
            if not all([self.auth_url, self.token_url, self.jwks_url]):
                raise ValueError("Provider missing required URLs and issuer_url")

            return {
                "auth_url": self.auth_url,
                "token_url": self.token_url,
                "jwks_url": self.jwks_url,
                "userinfo_url": self.userinfo_url,
                "issuer": self.auth_url.split("/authorize")[
                    0
                ],  # Basic issuer extraction
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope,
            }

    def __repr__(self) -> str:
        return f"<OIDCProvider {self.name}>"
