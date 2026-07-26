"""
ArtifactCodec abstract interface.
"""

from abc import ABC, abstractmethod
from typing import Any
from graph_storage.model import ArtifactHeader, VersionRef


class ArtifactCodec(ABC):
    """Abstract interface for serializing and deserializing storage artifacts."""

    @abstractmethod
    def encode(self, payload: Any) -> bytes:
        """Encode an in-memory storage artifact payload into raw bytes."""
        ...

    @abstractmethod
    def decode(self, data: bytes) -> Any:
        """Decode raw bytes back into an in-memory storage artifact payload."""
        ...

    @abstractmethod
    def header(self, data: bytes) -> ArtifactHeader:
        """Extract the domain header descriptor from serialized byte data."""
        ...

    @abstractmethod
    def schema_version(self) -> VersionRef:
        """Return the schema version reference supported by this codec."""
        ...
