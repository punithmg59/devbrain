"""
core/symbol_table/exceptions.py
--------------------------------
Domain exceptions for Symbol Table Builder & Immutable SymbolTable.
"""


class SymbolTableError(Exception):
    """Base exception for all symbol table errors."""
    pass


class IndexConsistencyError(SymbolTableError):
    """Raised when symbol table index consistency validation fails."""
    pass


class SymbolTableValidationError(SymbolTableError):
    """Raised when SymbolTable structural validation fails."""
    pass


class SymbolTableSerializationError(SymbolTableError):
    """Raised when SymbolTable serialization or deserialization fails."""
    pass
