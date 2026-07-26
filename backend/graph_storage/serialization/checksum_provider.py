"""
ChecksumProvider abstraction and concrete implementations.
"""

import hashlib
import zlib
from abc import ABC, abstractmethod

from graph_storage.exceptions import SerializationError


class ChecksumProvider(ABC):
    """Abstract interface for algorithm-specific checksum providers."""

    @abstractmethod
    def algorithm_id(self) -> int:
        """Return numeric algorithm identifier."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Return algorithm string name."""
        ...

    @abstractmethod
    def compute(self, data: bytes) -> str:
        """Compute hex checksum string for payload data."""
        ...

    def verify(self, data: bytes, expected_checksum: str) -> bool:
        """Verify payload data against expected checksum."""
        if not data or not expected_checksum:
            return False
        return self.compute(data).lower() == expected_checksum.lower()


class SHA256Provider(ChecksumProvider):
    """SHA-256 checksum provider (ID: 1)."""

    def algorithm_id(self) -> int:
        return 1

    def name(self) -> str:
        return "SHA256"

    def compute(self, data: bytes) -> str:
        if data is None:
            raise SerializationError("Cannot compute checksum for None data")
        return hashlib.sha256(data).hexdigest()


class CRC32Provider(ChecksumProvider):
    """CRC32 checksum provider (ID: 2)."""

    def algorithm_id(self) -> int:
        return 2

    def name(self) -> str:
        return "CRC32"

    def compute(self, data: bytes) -> str:
        if data is None:
            raise SerializationError("Cannot compute checksum for None data")
        return hex(zlib.crc32(data) & 0xFFFFFFFF)[2:].zfill(8)


class SHA512Provider(ChecksumProvider):
    """SHA-512 checksum provider (ID: 3)."""

    def algorithm_id(self) -> int:
        return 3

    def name(self) -> str:
        return "SHA512"

    def compute(self, data: bytes) -> str:
        if data is None:
            raise SerializationError("Cannot compute checksum for None data")
        return hashlib.sha512(data).hexdigest()


class BLAKE3Provider(ChecksumProvider):
    """BLAKE3 placeholder provider (ID: 4) falling back to SHA256 if blake3 package is absent."""

    def algorithm_id(self) -> int:
        return 4

    def name(self) -> str:
        return "BLAKE3"

    def compute(self, data: bytes) -> str:
        if data is None:
            raise SerializationError("Cannot compute checksum for None data")
        try:
            import blake3  # type: ignore
            return blake3.blake3(data).hexdigest()
        except ImportError:
            # Fallback to SHA256 when blake3 C-extension is not installed
            return hashlib.sha256(data).hexdigest()
