"""
Exceptions package for Graph Storage domain exception definitions.
"""

from graph_storage.exceptions.exceptions import (
    ArtifactCorruptedError,
    BackendUnavailableError,
    ChecksumMismatchError,
    CodecRegistrationError,
    GraphStorageError,
    HeaderDecodeError,
    SegmentNotFoundError,
    SerializationError,
    StorageIOError,
    StoragePermissionError,
    TransactionError,
    UnsupportedVersionError,
)

__all__ = [
    "GraphStorageError",
    "StorageIOError",
    "BackendUnavailableError",
    "SegmentNotFoundError",
    "StoragePermissionError",
    "TransactionError",
    "SerializationError",
    "HeaderDecodeError",
    "ChecksumMismatchError",
    "UnsupportedVersionError",
    "ArtifactCorruptedError",
    "CodecRegistrationError",
]
