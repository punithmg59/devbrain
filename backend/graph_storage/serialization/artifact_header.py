"""
ArtifactHeader binary format definition and packing codec.
"""

import struct
from dataclasses import dataclass
from graph_storage.exceptions import GraphStorageError
from graph_storage.model import VersionRef

MAGIC_BYTES = b"DBSG"
HEADER_FORMAT = ">4sHHHHHHQI8s"  # Big-endian: magic(4s), maj, min, pat, enc_maj, enc_min, alg, len(Q), flags(I), res(8s)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 36 bytes


@dataclass(frozen=True)
class ArtifactHeader:
    """Immutable binary header for storage artifacts."""

    magic_bytes: bytes
    schema_version: VersionRef
    encoding_version: VersionRef
    checksum_algorithm_id: int
    payload_length: int
    flags: int = 0
    reserved: bytes = b"\x00" * 8

    def encode(self) -> bytes:
        """Pack header into binary bytes."""
        return struct.pack(
            HEADER_FORMAT,
            self.magic_bytes,
            self.schema_version.major,
            self.schema_version.minor,
            self.schema_version.patch,
            self.encoding_version.major,
            self.encoding_version.minor,
            self.checksum_algorithm_id,
            self.payload_length,
            self.flags,
            self.reserved[:8].ljust(8, b"\x00"),
        )

    @classmethod
    def decode(cls, data: bytes) -> "ArtifactHeader":
        """Unpack header from binary bytes."""
        if len(data) < HEADER_SIZE:
            raise GraphStorageError(
                f"Binary data size ({len(data)} bytes) is smaller than minimum header size ({HEADER_SIZE} bytes)"
            )

        magic, maj, min_, pat, enc_maj, enc_min, alg_id, length, flags, res = struct.unpack(
            HEADER_FORMAT, data[:HEADER_SIZE]
        )

        if magic != MAGIC_BYTES:
            raise GraphStorageError(f"Invalid artifact magic number: {magic!r}, expected {MAGIC_BYTES!r}")

        return cls(
            magic_bytes=magic,
            schema_version=VersionRef(major=maj, minor=min_, patch=pat),
            encoding_version=VersionRef(major=enc_maj, minor=enc_min, patch=0),
            checksum_algorithm_id=alg_id,
            payload_length=length,
            flags=flags,
            reserved=res,
        )
