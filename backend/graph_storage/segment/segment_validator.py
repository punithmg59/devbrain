"""
SegmentValidator implementation for validating storage segment payload size, structure, and identifiers.
"""

import re
from graph_storage.exceptions import GraphStorageError, StorageIOError
from graph_storage.model import SegmentId


class SegmentValidator:
    """Validation utility for storage segments."""

    _ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

    @classmethod
    def validate_identifier(cls, segment_id: SegmentId) -> None:
        """Validate segment identifier format and non-emptiness."""
        if not segment_id or not segment_id.value or not segment_id.value.strip():
            raise GraphStorageError("Segment identifier cannot be empty")
        if not cls._ID_PATTERN.match(segment_id.value):
            raise GraphStorageError(f"Invalid characters in segment identifier: '{segment_id.value}'")

    @classmethod
    def validate_size(cls, data: bytes, max_size: int = 104857600) -> None:
        """Validate segment payload size boundaries."""
        if data is None:
            raise GraphStorageError("Segment data payload cannot be None")
        if len(data) == 0:
            raise GraphStorageError("Segment payload cannot be empty (0 bytes)")
        if len(data) > max_size:
            raise StorageIOError(f"Segment size ({len(data)} bytes) exceeds max limit ({max_size} bytes)")

    @classmethod
    def validate_structure(cls, data: bytes) -> None:
        """Validate structural payload integrity (non-null and non-empty)."""
        if not data or len(data) == 0:
            raise GraphStorageError("Segment data failed structural validation: empty payload")
