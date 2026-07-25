"""
core/type_reference_edges/exceptions.py
----------------------------------------
Domain exceptions for Type Reference Edge Builder.
"""


class TypeReferenceBuilderError(Exception):
    """Base exception for all type reference edge builder errors."""
    pass


class TypeReferenceResolutionError(TypeReferenceBuilderError):
    """Raised when an unhandled error occurs during type symbol resolution."""
    pass


class TypeReferenceValidationError(TypeReferenceBuilderError):
    """Raised when type reference edge validation fails."""
    pass


class TypeReferenceSerializationError(TypeReferenceBuilderError):
    """Raised when type reference edge serialization or deserialization fails."""
    pass
