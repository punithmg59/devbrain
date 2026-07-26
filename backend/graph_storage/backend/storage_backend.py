"""
StorageBackend abstract interface.
"""

from abc import ABC, abstractmethod
from typing import List
from graph_storage.model import SegmentId, SegmentDescriptor, StorageHealth


class StorageBackend(ABC):
    """Abstract interface for domain-driven physical storage backends."""

    @abstractmethod
    def exists_segment(self, segment_id: SegmentId) -> bool:
        """Check if a storage segment exists in physical storage."""
        ...

    @abstractmethod
    def read_segment(self, segment_id: SegmentId) -> bytes:
        """Read binary data for the specified storage segment."""
        ...

    @abstractmethod
    def write_segment(self, segment_id: SegmentId, data: bytes) -> SegmentDescriptor:
        """Write binary data for the specified storage segment and return its descriptor."""
        ...

    @abstractmethod
    def delete_segment(self, segment_id: SegmentId) -> bool:
        """Delete a storage segment by its segment identifier."""
        ...

    @abstractmethod
    def list_segments(self) -> List[SegmentDescriptor]:
        """List descriptors for all available storage segments."""
        ...

    @abstractmethod
    def health(self) -> StorageHealth:
        """Retrieve operational health details of the storage backend."""
        ...
