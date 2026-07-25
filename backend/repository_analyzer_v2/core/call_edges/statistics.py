"""
core/call_edges/statistics.py
------------------------------
Execution metrics and statistics model for Call Edge Builder.
"""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field


class CallEdgeStatistics(BaseModel):
    """
    Execution and resolution statistics for Call Edge Builder.
    """
    total_calls: int = Field(default=0, ge=0, description="Total call expressions processed")
    resolved_calls: int = Field(default=0, ge=0, description="Calls resolved to internal symbols")
    unresolved_calls: int = Field(default=0, ge=0, description="Calls unresolved or external")
    internal_calls: int = Field(default=0, ge=0, description="Internal repository call count")
    external_calls: int = Field(default=0, ge=0, description="External library call count")
    recursive_calls: int = Field(default=0, ge=0, description="Self-recursive call count")
    per_language_counts: Dict[str, int] = Field(default_factory=dict, description="Call count per language")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Builder execution duration in milliseconds")

    model_config = {
        "frozen": True
    }
