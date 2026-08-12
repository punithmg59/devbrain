"""Encryption service using AES-256-GCM with envelope format.

This module provides authenticated encryption for sensitive data at rest.
It uses a versioned envelope format to support key rotation and includes
associated data for context binding.
"""

import os
import base64
import struct
import logging
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from app.security.key_provider import get_key_provider

logger = logging.getLogger(__name__)

# Current envelope format version
ENVELOPE_VERSION = 1

# Nonce size for AES-GCM (12 bytes is recommended)
NONCE_SIZE = 12

# Key ID size in envelope (max 255 key IDs supported with 1 byte)
KEY_ID_SIZE = 1


class EncryptionError(Exception):
    """Base exception for encryption errors."""
    pass


class DecryptionError(EncryptionError):
    """Exception raised when decryption fails."""
    pass


class EncryptionService:
    """Service for encrypting and decrypting sensitive data.
    
    Uses AES-256-GCM with a versioned envelope format:
    
    envelope = version (1 byte) + key_id (1 byte) + nonce (12 bytes) + ciphertext + tag (16 bytes)
    
    The nonce is randomly generated for each encryption and stored in the envelope.
    The authentication tag is automatically appended by AESGCM.
    """
    
    def __init__(self):
        self._key_provider = get_key_provider()
    
    def _serialize_envelope(
        self,
        version: int,
        key_id: str,
        nonce: bytes,
        ciphertext: bytes,
    ) -> bytes:
        """Serialize envelope components into a single byte string.
        
        Args:
            version: Envelope version number
            key_id: Key identifier (must be single byte 0-255)
            nonce: Random nonce (12 bytes)
            ciphertext: Encrypted data with tag appended
            
        Returns:
            Serialized envelope as bytes
        """
        # Map key_id string to single byte (for simplicity, use hash or lookup)
        # For now, we'll use a simple mapping: 'default' -> 0, 'v1' -> 1, etc.
        key_id_byte = self._key_id_to_byte(key_id)
        
        # Build envelope: version + key_id + nonce + ciphertext
        envelope = struct.pack(
            f"BB{NONCE_SIZE}s",
            version,
            key_id_byte,
            nonce,
        )
        envelope += ciphertext
        
        return envelope
    
    def _deserialize_envelope(self, envelope: bytes) -> tuple[int, str, bytes, bytes]:
        """Deserialize envelope into components.
        
        Args:
            envelope: Serialized envelope bytes
            
        Returns:
            Tuple of (version, key_id, nonce, ciphertext_with_tag)
            
        Raises:
            DecryptionError: If envelope format is invalid
        """
        if len(envelope) < 2 + NONCE_SIZE:
            raise DecryptionError("Envelope too short")
        
        version, key_id_byte, nonce = struct.unpack(
            f"BB{NONCE_SIZE}s",
            envelope[:2 + NONCE_SIZE]
        )
        
        ciphertext_with_tag = envelope[2 + NONCE_SIZE:]
        
        key_id = self._byte_to_key_id(key_id_byte)
        
        return version, key_id, nonce, ciphertext_with_tag
    
    def _key_id_to_byte(self, key_id: str) -> int:
        """Convert key ID string to byte (0-255).
        
        Args:
            key_id: Key identifier string
            
        Returns:
            Byte value (0-255)
        """
        # Simple mapping for common key IDs
        mapping = {
            "default": 0,
            "v1": 1,
            "v2": 2,
            "v3": 3,
        }
        
        if key_id in mapping:
            return mapping[key_id]
        
        # For unknown key IDs, use a hash (modulo 256)
        # This is not ideal for production but works for development
        return hash(key_id) % 256
    
    def _byte_to_key_id(self, key_id_byte: int) -> str:
        """Convert byte to key ID string.
        
        Args:
            key_id_byte: Byte value (0-255)
            
        Returns:
            Key identifier string
        """
        # Reverse mapping for common key IDs
        reverse_mapping = {
            0: "default",
            1: "v1",
            2: "v2",
            3: "v3",
        }
        
        if key_id_byte in reverse_mapping:
            return reverse_mapping[key_id_byte]
        
        # For unknown bytes, return as string
        return f"key_{key_id_byte}"
    
    async def encrypt(
        self,
        plaintext: str | bytes,
        associated_data: Optional[bytes] = None,
    ) -> str:
        """Encrypt plaintext and return base64-encoded envelope.
        
        Args:
            plaintext: Data to encrypt (string or bytes)
            associated_data: Optional associated data for authentication
                            (e.g., user_id, repository_id for context binding)
            
        Returns:
            Base64-encoded encrypted envelope string
            
        Raises:
            EncryptionError: If encryption fails
        """
        if plaintext is None:
            raise EncryptionError("Cannot encrypt None")
        
        # Convert string to bytes if needed
        if isinstance(plaintext, str):
            plaintext_bytes = plaintext.encode('utf-8')
        else:
            plaintext_bytes = plaintext
        
        if not plaintext_bytes:
            # Empty string encrypts to empty envelope
            return ""
        
        try:
            # Get active key
            key_id = await self._key_provider.get_active_key_id()
            key = await self._key_provider.get_key(key_id)
            
            # Generate random nonce
            nonce = os.urandom(NONCE_SIZE)
            
            # Encrypt with AES-256-GCM
            aesgcm = AESGCM(key)
            ciphertext_with_tag = aesgcm.encrypt(
                nonce,
                plaintext_bytes,
                associated_data,
            )
            
            # Build envelope
            envelope = self._serialize_envelope(
                ENVELOPE_VERSION,
                key_id,
                nonce,
                ciphertext_with_tag,
            )
            
            # Return base64-encoded envelope
            return base64.urlsafe_b64encode(envelope).decode('ascii')
            
        except Exception as e:
            logger.error("Encryption failed: %s", e)
            raise EncryptionError(f"Encryption failed: {e}") from e
    
    async def decrypt(
        self,
        encrypted_envelope: str,
        associated_data: Optional[bytes] = None,
    ) -> str:
        """Decrypt base64-encoded envelope and return plaintext string.
        
        Args:
            encrypted_envelope: Base64-encoded encrypted envelope
            associated_data: Optional associated data for authentication
                            (must match what was used during encryption)
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            DecryptionError: If decryption fails or authentication fails
        """
        if not encrypted_envelope:
            return ""
        
        try:
            # Decode base64
            envelope = base64.urlsafe_b64decode(encrypted_envelope)
            
            # Deserialize envelope
            version, key_id, nonce, ciphertext_with_tag = self._deserialize_envelope(
                envelope
            )
            
            # Check version compatibility
            if version != ENVELOPE_VERSION:
                logger.warning(
                    "Envelope version %d differs from current version %d",
                    version,
                    ENVELOPE_VERSION,
                )
                # For now, we only support version 1
                if version > ENVELOPE_VERSION:
                    raise DecryptionError(
                        f"Envelope version {version} is not supported "
                        f"(current version: {ENVELOPE_VERSION})"
                    )
            
            # Get decryption key
            if not await self._key_provider.key_exists(key_id):
                raise DecryptionError(
                    f"Decryption key '{key_id}' not available (key rotation may be needed)"
                )
            
            key = await self._key_provider.get_key(key_id)
            
            # Decrypt with AES-256-GCM
            aesgcm = AESGCM(key)
            plaintext_bytes = aesgcm.decrypt(
                nonce,
                ciphertext_with_tag,
                associated_data,
            )
            
            # Return as string
            return plaintext_bytes.decode('utf-8')
            
        except InvalidTag:
            logger.error("Decryption failed: authentication tag invalid")
            raise DecryptionError(
                "Decryption failed: ciphertext may have been tampered with"
            ) from None
        except DecryptionError:
            raise
        except Exception as e:
            logger.error("Decryption failed: %s", e)
            raise DecryptionError(f"Decryption failed: {e}") from e
    
    async def encrypt_bytes(
        self,
        plaintext: bytes,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """Encrypt bytes and return envelope as bytes.
        
        Args:
            plaintext: Data to encrypt (bytes)
            associated_data: Optional associated data for authentication
            
        Returns:
            Raw envelope bytes (not base64-encoded)
            
        Raises:
            EncryptionError: If encryption fails
        """
        if plaintext is None:
            raise EncryptionError("Cannot encrypt None")
        
        if not plaintext:
            return b""
        
        try:
            # Get active key
            key_id = await self._key_provider.get_active_key_id()
            key = await self._key_provider.get_key(key_id)
            
            # Generate random nonce
            nonce = os.urandom(NONCE_SIZE)
            
            # Encrypt with AES-256-GCM
            aesgcm = AESGCM(key)
            ciphertext_with_tag = aesgcm.encrypt(
                nonce,
                plaintext,
                associated_data,
            )
            
            # Build envelope
            envelope = self._serialize_envelope(
                ENVELOPE_VERSION,
                key_id,
                nonce,
                ciphertext_with_tag,
            )
            
            return envelope
            
        except Exception as e:
            logger.error("Encryption failed: %s", e)
            raise EncryptionError(f"Encryption failed: {e}") from e
    
    async def decrypt_bytes(
        self,
        encrypted_envelope: bytes,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt envelope bytes and return plaintext bytes.
        
        Args:
            encrypted_envelope: Raw envelope bytes
            associated_data: Optional associated data for authentication
            
        Returns:
            Decrypted plaintext bytes
            
        Raises:
            DecryptionError: If decryption fails or authentication fails
        """
        if not encrypted_envelope:
            return b""
        
        try:
            # Deserialize envelope
            version, key_id, nonce, ciphertext_with_tag = self._deserialize_envelope(
                encrypted_envelope
            )
            
            # Check version compatibility
            if version != ENVELOPE_VERSION:
                logger.warning(
                    "Envelope version %d differs from current version %d",
                    version,
                    ENVELOPE_VERSION,
                )
                if version > ENVELOPE_VERSION:
                    raise DecryptionError(
                        f"Envelope version {version} is not supported "
                        f"(current version: {ENVELOPE_VERSION})"
                    )
            
            # Get decryption key
            if not await self._key_provider.key_exists(key_id):
                raise DecryptionError(
                    f"Decryption key '{key_id}' not available (key rotation may be needed)"
                )
            
            key = await self._key_provider.get_key(key_id)
            
            # Decrypt with AES-256-GCM
            aesgcm = AESGCM(key)
            plaintext_bytes = aesgcm.decrypt(
                nonce,
                ciphertext_with_tag,
                associated_data,
            )
            
            return plaintext_bytes
            
        except InvalidTag:
            logger.error("Decryption failed: authentication tag invalid")
            raise DecryptionError(
                "Decryption failed: ciphertext may have been tampered with"
            ) from None
        except DecryptionError:
            raise
        except Exception as e:
            logger.error("Decryption failed: %s", e)
            raise DecryptionError(f"Decryption failed: {e}") from e


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get the global encryption service instance.
    
    Returns:
        EncryptionService instance
    """
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    
    return _encryption_service
