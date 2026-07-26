"""
IntegrityPolicy, EncryptionPolicy, SecurityPolicy models, and KeyManager abstract interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from graph_storage.security.access_policy import AccessPolicy


@dataclass(frozen=True)
class IntegrityPolicy:
    """Immutable tamper detection and verification policy."""

    tamper_detection_enabled: bool = True
    verify_checksum_on_read: bool = True
    checksum_algorithm: str = "SHA256"


@dataclass(frozen=True)
class EncryptionPolicy:
    """Immutable architecture configuration for encryption (future implementation)."""

    encryption_enabled: bool = False
    algorithm: str = "AES-256-GCM"
    key_identifier: str = "default_key_001"
    rotation_policy: str = "monthly"


@dataclass(frozen=True)
class SecurityPolicy:
    """Aggregated immutable security policy configuration."""

    access_policy: AccessPolicy = field(default_factory=AccessPolicy)
    integrity_policy: IntegrityPolicy = field(default_factory=IntegrityPolicy)
    encryption_policy: EncryptionPolicy = field(default_factory=EncryptionPolicy)
    audit_enabled: bool = True
    session_timeout_seconds: float = 86400.0


class KeyManager(ABC):
    """Abstract interface for cryptographic key lifecycle management (future implementation)."""

    @abstractmethod
    def get_key(self, key_identifier: str) -> bytes: ...

    @abstractmethod
    def rotate_key(self, key_identifier: str) -> str: ...

    @abstractmethod
    def revoke_key(self, key_identifier: str) -> bool: ...

    @abstractmethod
    def validate_key(self, key_identifier: str) -> bool: ...
