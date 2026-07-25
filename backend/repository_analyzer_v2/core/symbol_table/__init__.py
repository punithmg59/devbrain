"""
core/symbol_table Package
-------------------------
Canonical Immutable SymbolTable for DevBrain.
"""

from core.symbol_table.builder import SymbolTableBuilder
from core.symbol_table.diagnostics import (
    SymbolTableDiagnostic,
    SymbolTableDiagnostics,
)
from core.symbol_table.exceptions import (
    IndexConsistencyError,
    SymbolTableError,
    SymbolTableSerializationError,
    SymbolTableValidationError,
)
from core.symbol_table.indexes import SymbolIndexSet
from core.symbol_table.interfaces import (
    ISymbolTable,
    ISymbolTableBuilderFacade,
)
from core.symbol_table.models import SymbolTable, SymbolTableStatistics
from core.symbol_table.queries import SymbolTableQueryEngine
from core.symbol_table.serialization import (
    SYMBOL_TABLE_VERSION,
    dict_to_table,
    hash_symbol_table,
    json_to_table,
    table_to_dict,
    table_to_json,
)
from core.symbol_table.validator import SymbolTableValidator

__all__ = [
    # Facade & Models
    "SymbolTableBuilder",
    "SymbolTable",
    "SymbolTableStatistics",
    "SymbolIndexSet",
    # Queries & Engine
    "SymbolTableQueryEngine",
    # Diagnostics
    "SymbolTableDiagnostic",
    "SymbolTableDiagnostics",
    # Validation
    "SymbolTableValidator",
    # Interfaces
    "ISymbolTable",
    "ISymbolTableBuilderFacade",
    # Exceptions
    "SymbolTableError",
    "IndexConsistencyError",
    "SymbolTableValidationError",
    "SymbolTableSerializationError",
    # Serialization
    "SYMBOL_TABLE_VERSION",
    "table_to_dict",
    "dict_to_table",
    "table_to_json",
    "json_to_table",
    "hash_symbol_table",
]
