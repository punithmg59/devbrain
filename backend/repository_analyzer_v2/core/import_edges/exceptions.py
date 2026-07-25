"""
core/import_edges/exceptions.py
--------------------------------
Domain exceptions for Import Edge Builder.
"""


class ImportBuilderError(Exception):
    """Base exception for all import edge builder errors."""
    pass


class ImportResolutionError(ImportBuilderError):
    """Raised when an unhandled error occurs during import symbol resolution."""
    pass


class ImportValidationError(ImportBuilderError):
    """Raised when import edge validation fails."""
    pass


class ImportSerializationError(ImportBuilderError):
    """Raised when import edge serialization or deserialization fails."""
    pass
