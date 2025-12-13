"""Simple OIDC service with minimal dependencies."""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple

import jwt
import requests
from flask import current_app

from app import db
from app.models.user import User


class OIDCService:
    """Simple OIDC service with minimal dependencies."""

    # In-memory JWKS cache
    _jwks_cache: Dict[str, Dict] = {}
    _jwks_cache_time: Dict[str, datetime] = {}
    JWKS_CACHE_DURATION = timedelta(hours=24)  # Refresh once per day

    @staticmethod
    def base64url_encode(data: bytes) -> str:
        """Proper base64url encoding without character stripping."""
        return base64.urlsafe_b64encode(data).decode("utf-8").replace("=", "")

    @staticmethod
    def generate_pkce() -> Tuple[str, str, str, str]:
        """Generate PKCE code verifier, challenge, state and nonce with proper encoding."""
        # Generate secure random code verifier (43-128 characters)
        code_verifier = OIDCService.base64url_encode(secrets.token_bytes(32))

        # Generate code challenge
        challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = OIDCService.base64url_encode(challenge_bytes)

        # Generate state for CSRF protection
        state = OIDCService.base64url_encode(secrets.token_bytes(16))

        # Generate nonce for replay protection
        nonce = OIDCService.base64url_encode(secrets.token_bytes(16))

        return code_verifier, code_challenge, state, nonce

    @staticmethod
    def discover_provider(issuer_url: str) -> Dict[str, str]:
        """Discover OIDC provider endpoints using standardized discovery."""
        discovery_url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"

        try:
            response = requests.get(discovery_url, timeout=10)
            response.raise_for_status()
            config = response.json()

            # Validate required fields
            required_fields = [
                "authorization_endpoint",
                "token_endpoint",
                "jwks_uri",
                "issuer",
            ]
            for field in required_fields:
                if field not in config:
                    raise ValueError(
                        f"Missing required field '{field}' in provider configuration"
                    )

            return {
                "auth_url": config["authorization_endpoint"],
                "token_url": config["token_endpoint"],
                "jwks_url": config["jwks_uri"],
                "userinfo_url": config.get("userinfo_endpoint"),
                "issuer": config["issuer"],
            }
        except requests.RequestException as e:
            raise ValueError(f"Failed to discover provider: {e}")

    @staticmethod
    def build_auth_url(
        provider_data: Dict,
        redirect_uri: str,
        code_challenge: str,
        state: str,
        nonce: str,
    ) -> str:
        """Build authorization URL with PKCE and nonce."""
        params = {
            "response_type": "code",
            "client_id": provider_data["client_id"],
            "redirect_uri": redirect_uri,
            "scope": provider_data.get("scope", "openid email profile"),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "nonce": nonce,
        }

        return f"{provider_data['auth_url']}?" + "&".join(
            f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()
        )

    @staticmethod
    def exchange_code_for_tokens(
        provider_data: Dict, code: str, redirect_uri: str, code_verifier: str
    ) -> Dict:
        """Exchange authorization code for tokens."""
        data = {
            "grant_type": "authorization_code",
            "client_id": provider_data["client_id"],
            "client_secret": provider_data["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }

        response = requests.post(
            provider_data["token_url"],
            data=data,
            timeout=10,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_cached_jwks(jwks_url: str) -> Dict:
        """Get JWKS keys with caching."""
        now = datetime.now(timezone.utc)

        # Check cache
        if (
            jwks_url in OIDCService._jwks_cache
            and jwks_url in OIDCService._jwks_cache_time
            and now - OIDCService._jwks_cache_time[jwks_url]
            < OIDCService.JWKS_CACHE_DURATION
        ):
            return OIDCService._jwks_cache[jwks_url]

        # Fetch new keys
        try:
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()
            jwks = response.json()

            # Cache the result
            OIDCService._jwks_cache[jwks_url] = jwks
            OIDCService._jwks_cache_time[jwks_url] = now

            return jwks
        except requests.RequestException as e:
            # If we have cached keys and network fails, use cached keys
            if jwks_url in OIDCService._jwks_cache:
                current_app.logger.warning(
                    f"Using cached JWKS due to network error: {e}"
                )
                return OIDCService._jwks_cache[jwks_url]
            raise ValueError(f"Failed to fetch JWKS keys: {e}")

    @staticmethod
    def validate_id_token(
        id_token: str, provider_data: Dict, stored_nonce: str
    ) -> Dict:
        """Validate ID token with comprehensive checks."""
        try:
            # Get JWKS keys
            jwks = OIDCService.get_cached_jwks(provider_data["jwks_url"])

            # Decode without verification first to get header
            unverified_header = jwt.get_unverified_header(id_token)
            kid = unverified_header.get("kid")

            if not kid:
                raise ValueError("Missing 'kid' in token header")

            # Find the matching key
            key_data = None
            for key in jwks["keys"]:
                if key.get("kid") == kid:
                    key_data = key
                    break

            if not key_data:
                raise ValueError(f"Key ID '{kid}' not found in JWKS")

            # Decode and verify token
            # PyJWT automatically handles various algorithms
            decoded_token = jwt.decode(
                id_token,
                key_data,  # PyJWT can directly use JWKS key data
                algorithms=[
                    "RS256",
                    "RS384",
                    "RS512",
                    "PS256",
                    "PS384",
                    "PS512",
                    "ES256",
                    "ES384",
                    "ES512",
                    "HS256",
                    "HS384",
                    "HS512",
                ],
                audience=provider_data["client_id"],
                issuer=provider_data["issuer"],
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iat": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                    "require": ["exp", "iat", "sub", "aud", "iss"],
                    "leeway": 60,  # 60 seconds clock skew tolerance
                },
            )

            # Validate nonce to prevent replay attacks
            if "nonce" not in decoded_token:
                raise ValueError("Missing 'nonce' in ID token")

            if decoded_token["nonce"] != stored_nonce:
                raise ValueError("Invalid nonce - possible replay attack")

            return decoded_token

        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid ID token: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"ID token validation error: {e}")
            raise ValueError(f"Token validation failed: {str(e)}")

    @staticmethod
    def find_or_create_user(claims: Dict, provider_name: str) -> User:
        """Find existing user or create new one from OIDC claims."""
        # Extract user information
        sub = claims.get("sub")
        email = claims.get("email")
        preferred_username = claims.get("preferred_username")

        if not sub:
            raise ValueError("Missing 'sub' claim in ID token")

        # Try to find user by OIDC identity first
        user = User.query.filter_by(
            auth_type="oidc", oidc_provider=provider_name, oidc_subject=sub
        ).first()

        if user:
            return user

        # If user with same email exists and is local, offer to link
        if email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.auth_type == "local":
                # In a real implementation, you might want to show a linking page
                # For now, we'll create a separate OIDC user
                pass

        # Generate unique username
        base_username = (
            preferred_username or email.split("@")[0]
            if email
            else f"oidc_user_{secrets.token_hex(4)}"
        )
        username = base_username

        # Ensure unique username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}_{counter}"
            counter += 1

        # Create new user
        user = User(
            username=username,
            email=email,
            auth_type="oidc",
            oidc_provider=provider_name,
            oidc_subject=sub,
            password_hash=None,  # No password for OIDC users
            is_active=True,
            is_admin=False,
        )

        db.session.add(user)
        db.session.commit()

        current_app.logger.info(
            f"Created new OIDC user: {username} from {provider_name}"
        )
        return user
