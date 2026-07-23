"""
analysis/symbol_table/__init__.py
----------------------------------
Phase 4.4 — Symbol Table & Symbol Index Package.

Exports the core symbol table data structures, builders, multi-index lookup engines,
and integrity validators.
"""

from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.symbol_table.symbol_index import SymbolIndex
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.symbol_table.symbol_validator import SymbolTableValidator

__all__ = [
    "SymbolTable",
    "SymbolTableBuilder",
    "SymbolIndex",
    "SymbolTableValidator",
]
