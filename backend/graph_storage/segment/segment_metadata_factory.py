"""
SegmentMetadataFactory for creating immutable SegmentMetadata objects.
"""

from graph_storage.model import PartitionId, SegmentId, SegmentMetadata
from graph_storage.segment.integrity_verifier import ChecksumAlgorithm, IntegrityVerifier


class SegmentMetadataFactory:
    """Factory for instantiating immutable SegmentMetadata objects."""

    @classmethod
    def create_metadata(
        cls,
        segment_id: SegmentId,
        data: bytes,
        partition_id: PartitionId = PartitionId("default"),
        record_count: int = 1,
        algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256,
    ) -> SegmentMetadata:
        """Construct a SegmentMetadata instance with computed checksum."""
        checksum = IntegrityVerifier.generate_checksum(data, algorithm)
        return SegmentMetadata(
            segment_id=segment_id,
            partition_id=partition_id,
            size_bytes=len(data),
            record_count=record_count,
            checksum=checksum,
        )
