"""Key provider abstraction for encryption keys.

This module provides an abstraction layer for encryption key management,
allowing DevBrain to support different key management systems (environment
variables, AWS KMS, Azure Key Vault, HashiCorp Vault, etc.) without changing
the encryption service.
"""

import os
import base64
import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class EncryptionKeyProvider(ABC):
    """Abstract base class for encryption key providers."""
    
    @abstractmethod
    async def get_key(self, key_id: str) -> bytes:
        """Get encryption key by ID.
        
        Args:
            key_id: Identifier for the key (e.g., 'default', 'v1', 'v2')
            
        Returns:
            Raw encryption key as bytes (32 bytes for AES-256)
            
        Raises:
            KeyError: If key_id is not found
            RuntimeError: If key provider is not properly configured
        """
        pass
    
    @abstractmethod
    async def get_active_key_id(self) -> str:
        """Get the ID of the currently active key for new encryptions.
        
        Returns:
            Key ID string
        """
        pass
    
    @abstractmethod
    async def key_exists(self, key_id: str) -> bool:
        """Check if a key exists.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if key exists, False otherwise
        """
        pass


class EnvironmentKeyProvider(EncryptionKeyProvider):
    """Key provider that loads keys from environment variables.
    
    This is the development/default implementation. Keys are loaded from
    environment variables in the format: DEVBRAIN_ENCRYPTION_KEY_<key_id>
    
    For production, consider using AWS KMS, Azure Key Vault, or similar.
    """
    
    def __init__(self):
        self._active_key_id: Optional[str] = None
        self._keys: dict[str, bytes] = {}
        self._initialized = False
    
    def _initialize(self):
        """Initialize keys from environment variables or config."""
        if self._initialized:
            return
        
        settings = get_settings()
        
        # Load the default/active key from environment or config
        default_key_b64 = os.environ.get("DEVBRAIN_ENCRYPTION_KEY") or settings.encryption_key
        if not default_key_b64:
            logger.warning(
                "DEVBRAIN_ENCRYPTION_KEY not set in environment or config. "
                "Encryption will not be available in production."
            )
            raise RuntimeError(
                "DEVBRAIN_ENCRYPTION_KEY environment variable or config.encryption_key is required for encryption. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        
        try:
            default_key = base64.urlsafe_b64decode(default_key_b64)
            if len(default_key) != 32:
                raise ValueError(f"Key must be 32 bytes for AES-256, got {len(default_key)}")
            self._keys["default"] = default_key
            self._active_key_id = "default"
            logger.info("Loaded default encryption key from environment")
        except Exception as e:
            logger.error("Failed to decode DEVBRAIN_ENCRYPTION_KEY: %s", e)
            raise RuntimeError(
                "DEVBRAIN_ENCRYPTION_KEY must be a valid base64-encoded 32-byte key"
            ) from e
        
        # Load additional keys for rotation (e.g., DEVBRAIN_ENCRYPTION_KEY_V1)
        for key_name, key_value in os.environ.items():
            if key_name.startswith("DEVBRAIN_ENCRYPTION_KEY_") and key_name != "DEVBRAIN_ENCRYPTION_KEY":
                key_id = key_name[len("DEVBRAIN_ENCRYPTION_KEY_"):].lower()
                try:
                    key = base64.urlsafe_b64decode(key_value)
                    if len(key) == 32:
                        self._keys[key_id] = key
                        logger.info("Loaded encryption key '%s' from environment", key_id)
                    else:
                        logger.warning(
                            "Key '%s' has wrong length (%d bytes), skipping", key_id, len(key)
                        )
                except Exception as e:
                    logger.warning("Failed to decode key '%s': %s", key_id, e)
        
        self._initialized = True
    
    async def get_key(self, key_id: str) -> bytes:
        """Get encryption key by ID."""
        if not self._initialized:
            self._initialize()
        
        if key_id not in self._keys:
            raise KeyError(f"Encryption key '{key_id}' not found")
        
        return self._keys[key_id]
    
    async def get_active_key_id(self) -> str:
        """Get the active key ID for new encryptions."""
        if not self._initialized:
            self._initialize()
        
        if not self._active_key_id:
            raise RuntimeError("No active encryption key configured")
        
        return self._active_key_id
    
    async def key_exists(self, key_id: str) -> bool:
        """Check if a key exists."""
        if not self._initialized:
            self._initialize()
        
        return key_id in self._keys


# Global key provider instance
_key_provider: Optional[EncryptionKeyProvider] = None


def get_key_provider() -> EncryptionKeyProvider:
    """Get the global key provider instance.
    
    Returns:
        EncryptionKeyProvider instance
        
    Raises:
        RuntimeError: If key provider is not initialized
    """
    global _key_provider
    
    if _key_provider is None:
        _key_provider = EnvironmentKeyProvider()
    
    return _key_provider


def set_key_provider(provider: EncryptionKeyProvider) -> None:
    """Set a custom key provider (for testing or production KMS).
    
    Args:
        provider: Custom EncryptionKeyProvider instance
    """
    global _key_provider
    _key_provider = provider
