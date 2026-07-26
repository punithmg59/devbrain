"""
SegmentReader implementation delegating physical reads to SegmentRepository.
"""

from graph_storage.exceptions import GraphStorageError
from graph_storage.model import SegmentId, SegmentMetadata
from graph_storage.segment.integrity_verifier import IntegrityVerifier
from graph_storage.segment.segment_metadata_factory import SegmentMetadataFactory
from graph_storage.segment.segment_repository import SegmentRepository
from graph_storage.segment.segment_validator import SegmentValidator


class SegmentReader:
    """Component responsible for reading and verifying segment data from repository."""

    def __init__(self, repository: SegmentRepository):
        self.repository = repository

    def read_segment(self, segment_id: SegmentId) -> bytes:
        """Read and structurally validate segment data payload from repository."""
        SegmentValidator.validate_identifier(segment_id)
        data = self.repository.load(segment_id)
        SegmentValidator.validate_structure(data)
        return data

    def read_metadata(self, segment_id: SegmentId) -> SegmentMetadata:
        """Read segment data and construct metadata descriptor."""
        SegmentValidator.validate_identifier(segment_id)
        data = self.read_segment(segment_id)
        return SegmentMetadataFactory.create_metadata(segment_id, data)

    def verify_integrity(self, segment_id: SegmentId, expected_checksum: str) -> bool:
        """Verify checksum integrity of stored segment data."""
        try:
            data = self.read_segment(segment_id)
            return IntegrityVerifier.verify_checksum(data, expected_checksum)
        except GraphStorageError:
            return False
