"""
BinaryFormat specification separating binary format schema rules from codecs.
"""

import struct
from dataclasses import dataclass
from graph_storage.model import VersionRef

MAGIC_BYTES = b"DBSG"
HEADER_FORMAT = ">4sHHHHHHQI8s"  # Struct layout: 36 bytes total
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


@dataclass(frozen=True)
class BinaryFormatSpec:
    """Specification rules for binary artifact headers and layouts."""

    magic: bytes = MAGIC_BYTES
    header_format: str = HEADER_FORMAT
    header_size: int = HEADER_SIZE
    default_schema_version: VersionRef = VersionRef(1, 0, 0)
    default_encoding_version: VersionRef = VersionRef(1, 0, 0)


class BinaryFormat:
    """Central specification authority for binary format properties."""

    SPEC = BinaryFormatSpec()

    @classmethod
    def get_spec(cls) -> BinaryFormatSpec:
        return cls.SPEC
