"""
analysis/reference_resolution/__init__.py
------------------------------------------
Phase 4.7 — Reference Resolution Engine Package.

Exports identifier reference indexing, AST reference builder, reference resolution
coordinator, and reference validator engines.
"""

from analysis.reference_resolution.reference_builder import ReferenceBuilder
from analysis.reference_resolution.reference_index import ReferenceIndex
from analysis.reference_resolution.reference_resolver import ReferenceResolver
from analysis.reference_resolution.reference_validator import ReferenceValidator

__all__ = [
    "ReferenceIndex",
    "ReferenceBuilder",
    "ReferenceResolver",
    "ReferenceValidator",
]
