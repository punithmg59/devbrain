"""
ArtifactCodec abstract interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class ArtifactCodec(ABC):
    """Abstract interface for serializing and deserializing storage artifacts."""

    @abstractmethod
    def encode(self, payload: Any) -> bytes:
        """Encode an in-memory artifact payload into raw bytes."""
        ...

    @abstractmethod
    def decode(self, data: bytes) -> Any:
        """Decode raw bytes back into an in-memory artifact payload."""
        ...

    @abstractmethod
    def header(self, data: bytes) -> Dict[str, Any]:
        """Extract header metadata from serialized byte data."""
        ...

    @abstractmethod
    def schema_version(self) -> str:
        """Return the schema version supported by this codec."""
        ...
