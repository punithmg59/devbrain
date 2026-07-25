"""
core/symbol_extractor/exceptions.py
------------------------------------
Domain exceptions for Symbol Extractor & RawSymbolCollection.
"""


class SymbolExtractionError(Exception):
    """Base exception for all symbol extraction errors."""
    pass


class TemporaryIDError(SymbolExtractionError):
    """Raised when TemporaryExtractionID generation or validation fails."""
    pass


class SymbolExtractionValidationError(SymbolExtractionError):
    """Raised when RawSymbol or RawSymbolCollection validation fails."""
    pass


class ExtractorRegistryError(SymbolExtractionError):
    """Raised when language extractor lookup or registration fails."""
    pass


class SymbolExtractionSerializationError(SymbolExtractionError):
    """Raised when RawSymbolCollection serialization or deserialization fails."""
    pass
