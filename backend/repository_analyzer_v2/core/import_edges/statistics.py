"""
core/import_edges/statistics.py
--------------------------------
Execution metrics and statistics model for Import Edge Builder.
"""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field


class ImportEdgeStatistics(BaseModel):
    """
    Execution and resolution statistics for Import Edge Builder.
    """
    total_imports: int = Field(default=0, ge=0, description="Total import statements processed")
    resolved_imports: int = Field(default=0, ge=0, description="Imports resolved to internal symbols")
    unresolved_imports: int = Field(default=0, ge=0, description="Imports unresolved or external")
    internal_imports: int = Field(default=0, ge=0, description="Internal repository imports")
    external_imports: int = Field(default=0, ge=0, description="External library imports")
    per_language_counts: Dict[str, int] = Field(default_factory=dict, description="Import count per language")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Builder execution duration in milliseconds")

    model_config = {
        "frozen": True
    }
