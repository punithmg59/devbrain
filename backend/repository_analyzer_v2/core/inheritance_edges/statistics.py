"""
core/inheritance_edges/statistics.py
-------------------------------------
Execution metrics and statistics model for Inheritance Edge Builder.
"""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field


class InheritanceEdgeStatistics(BaseModel):
    """
    Execution and resolution statistics for Inheritance Edge Builder.
    """
    total_inheritance_edges: int = Field(default=0, ge=0, description="Total inheritance/implementation relationships processed")
    resolved_edges: int = Field(default=0, ge=0, description="Base types resolved to internal symbols")
    unresolved_edges: int = Field(default=0, ge=0, description="Base types unresolved or external")
    internal_edges: int = Field(default=0, ge=0, description="Internal repository inheritance count")
    external_edges: int = Field(default=0, ge=0, description="External framework inheritance count")
    interfaces_count: int = Field(default=0, ge=0, description="Interface implementation count")
    traits_count: int = Field(default=0, ge=0, description="Trait implementation count")
    per_language_counts: Dict[str, int] = Field(default_factory=dict, description="Inheritance count per language")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Builder execution duration in milliseconds")

    model_config = {
        "frozen": True
    }
