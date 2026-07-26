"""
SegmentManager as a lightweight facade orchestrating segment services.
"""

from typing import Dict, List, Optional

from graph_storage.backend.storage_backend import StorageBackend
from graph_storage.backend.storage_layout import StorageLayout
from graph_storage.model import SegmentDescriptor, SegmentId, SegmentMetadata
from graph_storage.segment.segment_command_service import SegmentCommandService
from graph_storage.segment.segment_metadata_service import SegmentMetadataService
from graph_storage.segment.segment_query_service import SegmentQueryService
from graph_storage.segment.segment_reader import SegmentReader
from graph_storage.segment.segment_repository import SegmentRepository
from graph_storage.segment.segment_state_machine import SegmentStateMachine
from graph_storage.segment.segment_writer import SegmentWriter


class SegmentManager:
    """Facade orchestrating SegmentCommandService, SegmentQueryService, and SegmentMetadataService."""

    def __init__(
        self,
        backend: StorageBackend,
        layout: Optional[StorageLayout] = None,
    ):
        self.repository = SegmentRepository(backend, layout)
        self.reader = SegmentReader(self.repository)
        self.writer = SegmentWriter(self.repository)
        self.state_machine = SegmentStateMachine()

        self.command_service = SegmentCommandService(self.repository, self.writer, self.state_machine)
        self.query_service = SegmentQueryService(self.repository, self.reader)
        self.metadata_service = SegmentMetadataService(self.repository, self.reader)

    def create_segment(self, segment_id: SegmentId, data: bytes) -> SegmentDescriptor:
        """Delegate segment creation to command service."""
        return self.command_service.create(segment_id, data)

    def load_segment(self, segment_id: SegmentId) -> bytes:
        """Delegate segment loading to query service."""
        return self.query_service.load(segment_id)

    def delete_segment(self, segment_id: SegmentId) -> bool:
        """Delegate segment deletion to command service."""
        return self.command_service.delete(segment_id)

    def segment_exists(self, segment_id: SegmentId) -> bool:
        """Delegate existence check to query service."""
        return self.query_service.exists(segment_id)

    def list_segments(self) -> List[SegmentDescriptor]:
        """Delegate segment listing to query service."""
        return self.query_service.list()

    def segment_metadata(self, segment_id: SegmentId) -> SegmentMetadata:
        """Delegate metadata query to metadata service."""
        return self.metadata_service.metadata(segment_id)

    def statistics(self) -> Dict[str, int]:
        """Delegate statistics query to metadata service."""
        return self.metadata_service.statistics()
