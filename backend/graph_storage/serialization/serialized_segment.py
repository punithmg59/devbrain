"""
SerializedSegment model definition.
"""

from dataclasses import dataclass
from graph_storage.model import SegmentId, VersionRef


@dataclass(frozen=True)
class SerializedSegment:
    """Immutable model representing the binary serialized form of a segment."""

    segment_id: SegmentId
    payload: bytes
    size_bytes: int
    checksum: str
    version: VersionRef
    compression_type: str = "none"
