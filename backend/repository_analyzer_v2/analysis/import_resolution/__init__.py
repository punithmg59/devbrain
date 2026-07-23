"""
analysis/import_resolution/__init__.py
---------------------------------------
Phase 4.6 — Import Resolution Engine Package.

Exports module indexing, import statement indexing, cross-file symbol linking,
import resolution coordination, and import validator engines.
"""

from analysis.import_resolution.import_index import ImportIndex
from analysis.import_resolution.import_linker import ImportLinker
from analysis.import_resolution.import_resolver import ImportResolver
from analysis.import_resolution.import_validator import ImportValidator
from analysis.import_resolution.module_index import ModuleIndex

__all__ = [
    "ModuleIndex",
    "ImportIndex",
    "ImportResolver",
    "ImportLinker",
    "ImportValidator",
]
