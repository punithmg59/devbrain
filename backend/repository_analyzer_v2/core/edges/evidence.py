"""
core/edges/evidence.py
-----------------------
Provenance, Evidence, and Versioning Models for DevBrain Edges.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from core.symbols.models import SourceRange


class EdgeEvidence(BaseModel):
    """
    Supporting evidence capturing provenance, source ranges, AST nodes, and builder details.
    Allows downstream explainability and auditing.
    """
    file_path: Optional[str] = Field(default=None, description="Source file path where relationship was extracted")
    source_range: Optional[SourceRange] = Field(default=None, description="Source code range location")
    ast_node_ref: Optional[Dict[str, Any]] = Field(default=None, description="Raw parser AST node reference")
    parser_ref: Optional[Dict[str, Any]] = Field(default=None, description="Parser job or result reference")
    stage_name: Optional[str] = Field(default=None, description="Extraction stage name (e.g. Step 4.2 Import Edge Builder)")
    builder_name: Optional[str] = Field(default=None, description="Specific edge builder class or plugin name")
    confidence_source: Optional[str] = Field(default=None, description="Origin of confidence metric")
    explanation: Optional[str] = Field(default=None, description="Human-readable explanation of relationship rationale")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class EdgeOrigin(BaseModel):
    """Provenance tracking origin metadata."""
    creator: str = Field(default="devbrain.edge_builder", description="Entity or plugin that generated the edge")
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp"
    )
    stage: str = Field(default="Step 4", description="Pipeline stage classification")

    model_config = {
        "frozen": True
    }


class EdgeVersion(BaseModel):
    """Semantic versioning tag for Edge schema."""
    semver: str = Field(default="1.0.0", description="Semantic version string")

    model_config = {
        "frozen": True
    }
