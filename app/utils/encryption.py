"""
Database encryption utilities for Uptimo.

This module provides encryption/decryption functionality for sensitive data
stored in the database. Uses Fernet symmetric encryption from cryptography library.
"""

import os
import base64
import binascii
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class DatabaseEncryption:
    """Handles database encryption using Fernet symmetric encryption."""

    def __init__(self, key: Optional[str] = None):
        """Initialize encryption with provided key or generate new one."""
        if key:
            if isinstance(key, str):
                # Convert string key to bytes
                self.key = key.encode()
            else:
                self.key = key
        else:
            # Generate new key
            self.key = Fernet.generate_key()

        self._cipher = Fernet(self.key)

    @classmethod
    def from_password(
        cls, password: str, salt: Optional[bytes] = None
    ) -> "DatabaseEncryption":
        """
        Create encryption instance from password using PBKDF2 key derivation.

        Args:
            password: User password to derive key from
            salt: Optional salt for key derivation (generated if not provided)

        Returns:
            DatabaseEncryption instance with derived key
        """
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return cls(key.decode())

    def encrypt(self, data: str) -> str:
        """
        Encrypt string data.

        Args:
            data: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not data:
            return ""

        try:
            encrypted_data = self._cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted string data.

        Args:
            encrypted_data: Base64-encoded encrypted string

        Returns:
            Decrypted string

        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_data:
            return ""

        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._cipher.decrypt(decoded_data)
            return decrypted_data.decode()
        except (InvalidToken, binascii.Error, Exception) as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    def get_key_string(self) -> str:
        """Get the encryption key as a base64 string."""
        return self.key.decode()

    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key and return as base64 string."""
        return Fernet.generate_key().decode()

    @staticmethod
    def validate_key(key: str) -> bool:
        """
        Validate if the provided key is a valid Fernet key.

        Args:
            key: Key string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            Fernet(key.encode() if isinstance(key, str) else key)
            return True
        except Exception:
            return False


# Global encryption instance
_encryption_instance: Optional[DatabaseEncryption] = None


def get_encryption() -> DatabaseEncryption:
    """Get the global encryption instance."""
    global _encryption_instance
    if _encryption_instance is None:
        from flask import current_app

        key = current_app.config.get("DATABASE_ENCRYPTION_KEY")
        if not key:
            raise ValueError("DATABASE_ENCRYPTION_KEY not configured")
        _encryption_instance = DatabaseEncryption(key)
    return _encryption_instance


def init_encryption(key: str) -> None:
    """Initialize the global encryption instance with provided key."""
    global _encryption_instance
    _encryption_instance = DatabaseEncryption(key)


def encrypt_field(data: str) -> str:
    """Encrypt a field using the global encryption instance."""
    return get_encryption().encrypt(data)


def decrypt_field(encrypted_data: str) -> str:
    """Decrypt a field using the global encryption instance."""
    return get_encryption().decrypt(encrypted_data)


# Legacy compatibility
class FieldEncryption:
    """Legacy class for backward compatibility."""

    @staticmethod
    def encrypt(data: str) -> str:
        """Encrypt data using global encryption instance."""
        return encrypt_field(data)

    @staticmethod
    def decrypt(encrypted_data: str) -> str:
        """Decrypt data using global encryption instance."""
        return decrypt_field(encrypted_data)
