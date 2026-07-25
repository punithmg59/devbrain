"""
core/facade/models.py
---------------------
Immutable RepositoryAnalysisResult Domain Model for DependencyGraph Facade.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.dependency_graph import DependencyGraph
from core.graph_validation import DependencyGraphValidationReport
from core.symbol_builder import SemanticRepository


class RepositoryAnalysisResult(BaseModel):
    """
    Immutable container returned by DependencyGraphFacade containing complete repository analysis output.
    """
    repository_id: str = Field(..., description="Repository identifier")
    semantic_repository: SemanticRepository = Field(..., description="SemanticRepository output from Step 3.6")
    graph: DependencyGraph = Field(..., description="Unified DependencyGraph output from Step 4.6")
    validation_report: DependencyGraphValidationReport = Field(..., description="Validation report output from Step 4.7")
    duration_ms: float = Field(..., description="Total pipeline execution duration in milliseconds")
    version: str = Field(default="4.8.0", description="RepositoryAnalysisResult schema semver")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }
