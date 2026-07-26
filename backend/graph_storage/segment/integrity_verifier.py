"""
IntegrityVerifier component supporting algorithm-abstract checksum generation and verification.
"""

import hashlib
from enum import Enum, auto
from graph_storage.exceptions import GraphStorageError


class ChecksumAlgorithm(Enum):
    """Supported checksum algorithms for integrity verification."""
    SHA256 = auto()
    CRC32 = auto()
    BLAKE3 = auto()
    SHA512 = auto()


class IntegrityVerifier:
    """Checksum generation and verification engine."""

    @classmethod
    def generate_checksum(cls, data: bytes, algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256) -> str:
        """Generate hex checksum for data bytes using specified algorithm."""
        if not data:
            raise GraphStorageError("Cannot generate checksum for empty or None data")

        if algorithm == ChecksumAlgorithm.SHA256:
            return hashlib.sha256(data).hexdigest()
        elif algorithm == ChecksumAlgorithm.SHA512:
            return hashlib.sha512(data).hexdigest()
        elif algorithm == ChecksumAlgorithm.CRC32:
            import zlib
            return hex(zlib.crc32(data) & 0xFFFFFFFF)[2:].zfill(8)
        else:
            raise GraphStorageError(f"Unsupported checksum algorithm: {algorithm}")

    @classmethod
    def verify_checksum(
        cls,
        data: bytes,
        expected_checksum: str,
        algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256,
    ) -> bool:
        """Verify data bytes against expected hex checksum."""
        if not data or not expected_checksum:
            return False
        actual_checksum = cls.generate_checksum(data, algorithm)
        return actual_checksum.lower() == expected_checksum.lower()
