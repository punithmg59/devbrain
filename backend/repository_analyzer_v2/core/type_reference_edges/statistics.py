"""
core/type_reference_edges/statistics.py
---------------------------------------
Execution metrics and statistics model for Type Reference Edge Builder.
"""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field


class TypeReferenceEdgeStatistics(BaseModel):
    """
    Execution and resolution statistics for Type Reference Edge Builder.
    """
    total_type_references: int = Field(default=0, ge=0, description="Total compile-time type references processed")
    resolved_type_references: int = Field(default=0, ge=0, description="Types resolved to internal symbols")
    unresolved_type_references: int = Field(default=0, ge=0, description="Types unresolved or external/primitive")
    internal_type_references: int = Field(default=0, ge=0, description="Internal repository type count")
    external_type_references: int = Field(default=0, ge=0, description="External library or primitive type count")
    generic_references_count: int = Field(default=0, ge=0, description="Generic type container reference count")
    per_language_counts: Dict[str, int] = Field(default_factory=dict, description="Type reference count per language")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Builder execution duration in milliseconds")

    model_config = {
        "frozen": True
    }
