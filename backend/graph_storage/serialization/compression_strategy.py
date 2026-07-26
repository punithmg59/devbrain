"""
CompressionStrategy abstraction and NoCompression implementation.
"""

from abc import ABC, abstractmethod


class CompressionStrategy(ABC):
    """Abstract interface for payload compression strategies."""

    @abstractmethod
    def compression_name(self) -> str:
        """Return compression algorithm name."""
        ...

    @abstractmethod
    def compress(self, data: bytes) -> bytes:
        """Compress payload bytes."""
        ...

    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Decompress payload bytes."""
        ...


class NoCompression(CompressionStrategy):
    """Pass-through zero-compression strategy."""

    def compression_name(self) -> str:
        return "none"

    def compress(self, data: bytes) -> bytes:
        return data

    def decompress(self, data: bytes) -> bytes:
        return data
