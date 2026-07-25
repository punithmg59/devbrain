"""
core/symbol_identity/exceptions.py
-----------------------------------
Domain exceptions for Symbol Identity Builder & CanonicalSymbolCollection.
"""


class IdentityError(Exception):
    """Base exception for all symbol identity errors."""
    pass


class DuplicateSymbolError(IdentityError):
    """Raised when an unhandled duplicate symbol collision occurs."""
    pass


class NormalizationError(IdentityError):
    """Raised when QualifiedName or metadata normalization fails."""
    pass


class IdentityValidationError(IdentityError):
    """Raised when CanonicalSymbolCollection validation fails."""
    pass


class IdentitySerializationError(IdentityError):
    """Raised when CanonicalSymbolCollection serialization or deserialization fails."""
    pass
