"""
core/inheritance_edges/exceptions.py
-------------------------------------
Domain exceptions for Inheritance Edge Builder.
"""


class InheritanceBuilderError(Exception):
    """Base exception for all inheritance edge builder errors."""
    pass


class InheritanceResolutionError(InheritanceBuilderError):
    """Raised when an unhandled error occurs during base type resolution."""
    pass


class InheritanceValidationError(InheritanceBuilderError):
    """Raised when inheritance edge validation fails."""
    pass


class InheritanceSerializationError(InheritanceBuilderError):
    """Raised when inheritance edge serialization or deserialization fails."""
    pass
