"""
Domain exceptions for Graph Storage module.
"""


class GraphStorageError(Exception):
    """Base exception for all Graph Storage operations."""
    pass


class StorageIOError(GraphStorageError):
    """Raised when physical storage I/O fails."""
    pass


class BackendUnavailableError(GraphStorageError):
    """Raised when a storage backend is offline or unavailable."""
    pass


class SegmentNotFoundError(GraphStorageError):
    """Raised when a requested storage segment is not found."""
    pass


class StoragePermissionError(GraphStorageError):
    """Raised when storage access is denied due to permission issues."""
    pass


class TransactionError(GraphStorageError):
    """Raised when a transaction or lease operation fails in Graph Storage."""
    pass


class SerializationError(GraphStorageError):
    """Base exception for serialization and deserialization errors."""
    pass


class HeaderDecodeError(SerializationError):
    """Raised when parsing or unpacking a binary artifact header fails."""
    pass


class ChecksumMismatchError(SerializationError):
    """Raised when payload integrity verification fails due to checksum mismatch."""
    pass


class UnsupportedVersionError(SerializationError):
    """Raised when an unsupported schema or encoding version is encountered."""
    pass


class ArtifactCorruptedError(SerializationError):
    """Raised when a binary artifact payload is malformed or corrupted."""
    pass


class CodecRegistrationError(SerializationError):
    """Raised when codec lookup or registration fails."""
    pass
