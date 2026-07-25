"""
core/graph_validation/report.py
--------------------------------
Immutable DependencyGraphValidationReport Domain Model.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.graph_validation.diagnostics import ValidationDiagnostics
from core.graph_validation.statistics import ValidationStatistics


class DependencyGraphValidationReport(BaseModel):
    """
    Immutable validation quality report for a DependencyGraph.
    """
    is_valid: bool = Field(..., description="True if zero ERROR-level diagnostics were recorded")
    repository_id: str = Field(..., description="Repository identifier")
    validated_graph_hash: str = Field(..., description="Cryptographic SHA-256 hash of validated graph")
    total_nodes_validated: int = Field(default=0, ge=0, description="Total nodes inspected")
    total_edges_validated: int = Field(default=0, ge=0, description="Total edges inspected")
    error_count: int = Field(default=0, ge=0, description="Total error-level diagnostics recorded")
    warning_count: int = Field(default=0, ge=0, description="Total warning-level diagnostics recorded")
    diagnostics: ValidationDiagnostics = Field(..., description="Aggregated validation diagnostics")
    statistics: ValidationStatistics = Field(..., description="Validation execution statistics")
    version: str = Field(default="4.7.0", description="Validation report schema semver")
    summary: str = Field(..., description="Human-readable executive summary string")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }
