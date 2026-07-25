"""
core/symbol_builder/statistics.py
----------------------------------
Aggregated Statistics and Stage Timing models for SemanticRepository.
"""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field


class SemanticRepositoryStatistics(BaseModel):
    """
    Aggregated execution metrics and timings for the complete Symbol Pipeline.
    """
    total_files: int = Field(default=0, ge=0, description="Total source files processed")
    total_namespaces: int = Field(default=0, ge=0, description="Total namespace nodes constructed")
    total_raw_symbols: int = Field(default=0, ge=0, description="Total raw symbols extracted")
    total_canonical_symbols: int = Field(default=0, ge=0, description="Total canonical symbols produced")
    total_indexed_symbols: int = Field(default=0, ge=0, description="Total symbols indexed in SymbolTable")
    stage_timings_ms: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-stage timing breakdown in milliseconds"
    )
    duplicates_detected: int = Field(default=0, ge=0, description="Count of duplicate declarations")
    overloads_detected: int = Field(default=0, ge=0, description="Count of overloaded signatures")

    model_config = {
        "frozen": True
    }
