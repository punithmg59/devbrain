"""
core/graph_validation/statistics.py
------------------------------------
Execution metrics and statistics model for Dependency Graph Validation Framework.
"""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field


class ValidationStatistics(BaseModel):
    """
    Validation evaluation statistics and metrics.
    """
    total_nodes_validated: int = Field(default=0, ge=0, description="Total node count validated")
    total_edges_validated: int = Field(default=0, ge=0, description="Total edge count validated")
    orphan_nodes_count: int = Field(default=0, ge=0, description="Nodes with zero incoming or outgoing edges")
    rules_evaluated_count: int = Field(default=0, ge=0, description="Total validation rule evaluations executed")
    errors_by_category: Dict[str, int] = Field(default_factory=dict, description="Error counts per ValidationCategory")
    warnings_by_category: Dict[str, int] = Field(default_factory=dict, description="Warning counts per ValidationCategory")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Validation framework duration in milliseconds")

    model_config = {
        "frozen": True
    }
