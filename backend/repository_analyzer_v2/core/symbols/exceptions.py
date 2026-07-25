"""
core/symbols/exceptions.py
--------------------------
Domain exceptions for the Canonical Symbol Model.
"""


class SymbolError(Exception):
    """Base exception for all symbol domain errors."""
    pass


class SymbolIDError(SymbolError):
    """Raised when SymbolID generation or validation fails."""
    pass


class QualifiedNameError(SymbolError):
    """Raised when QualifiedName construction, parsing, or traversal fails."""
    pass


class SymbolValidationError(SymbolError):
    """Raised when symbol immutability or attribute validation fails."""
    pass


class SymbolSerializationError(SymbolError):
    """Raised when symbol serialization or deserialization fails."""
    pass
