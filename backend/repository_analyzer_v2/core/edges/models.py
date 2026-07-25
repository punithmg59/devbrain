"""
core/edges/models.py
--------------------
Canonical Edge Entity and Immutable EdgeCollection Container.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator

from core.edges.diagnostics import EdgeDiagnostics
from core.edges.enums import EdgeDirection, EdgeKind, EdgeStrength
from core.edges.evidence import EdgeEvidence, EdgeOrigin, EdgeVersion
from core.edges.exceptions import EdgeValidationError
from core.edges.ids import EdgeID
from core.edges.metadata import EdgeAttributes, EdgeMetadata
from core.symbols import Language, SymbolID


class Edge(BaseModel):
    """
    Canonical Immutable Edge Entity representing a relationship between two symbols.
    """
    id: EdgeID = Field(..., description="Deterministic, unique edge identifier")
    source_symbol_id: SymbolID = Field(..., description="Origin SymbolID")
    target_symbol_id: SymbolID = Field(..., description="Destination SymbolID")
    kind: EdgeKind = Field(..., description="Relationship classification kind")
    direction: EdgeDirection = Field(default=EdgeDirection.DIRECTED, description="Relationship directionality")
    strength: EdgeStrength = Field(default=EdgeStrength.NORMAL, description="Coupling strength classification")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score (0.0 - 1.0)")
    language: Language = Field(..., description="Programming language classification")
    repository_id: str = Field(..., description="Containing repository identifier")
    file_path: Optional[str] = Field(default=None, description="Source file path provenance")
    evidence: EdgeEvidence = Field(default_factory=EdgeEvidence, description="Supporting AST & location evidence")
    attributes: EdgeAttributes = Field(default_factory=EdgeAttributes, description="Key-value domain attributes")
    origin: EdgeOrigin = Field(default_factory=EdgeOrigin, description="Origin provenance tag")
    version: EdgeVersion = Field(default_factory=EdgeVersion, description="Edge schema version tag")
    metadata: EdgeMetadata = Field(default_factory=EdgeMetadata, description="Reserved namespace metadata")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("repository_id")
    @classmethod
    def _validate_repo_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise EdgeValidationError("Edge repository_id cannot be empty.")
        return v.strip()


class EdgeStatistics(BaseModel):
    """Execution and indexing metrics for EdgeCollection."""
    total_edges: int = Field(default=0, ge=0)
    edges_by_kind_counts: Dict[str, int] = Field(default_factory=dict)
    duration_ms: float = Field(default=0.0, ge=0.0)

    model_config = {
        "frozen": True
    }


class EdgeCollection(BaseModel):
    """
    Canonical, Immutable EdgeCollection Container storing relationship edges.
    """
    repository_id: str = Field(..., description="Repository identifier")
    edges: List[Edge] = Field(default_factory=list, description="List of relationship edges")
    edges_by_id: Dict[EdgeID, Edge] = Field(
        default_factory=dict,
        description="EdgeID to Edge mapping"
    )
    edges_by_source: Dict[SymbolID, List[EdgeID]] = Field(
        default_factory=dict,
        description="Source SymbolID to outgoing EdgeIDs index"
    )
    edges_by_target: Dict[SymbolID, List[EdgeID]] = Field(
        default_factory=dict,
        description="Target SymbolID to incoming EdgeIDs index"
    )
    edges_by_kind: Dict[EdgeKind, List[EdgeID]] = Field(
        default_factory=dict,
        description="EdgeKind to EdgeIDs index"
    )
    statistics: EdgeStatistics = Field(
        default_factory=EdgeStatistics,
        description="Edge collection metrics"
    )
    diagnostics: EdgeDiagnostics = Field(
        default_factory=EdgeDiagnostics,
        description="Diagnostics report"
    )

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("edges_by_id", mode="before")
    @classmethod
    def _validate_by_id_keys(cls, v: Any) -> Any:
        if isinstance(v, dict):
            new_dict = {}
            for k, val in v.items():
                key_obj = EdgeID(value=k) if isinstance(k, str) else k
                new_dict[key_obj] = val
            return new_dict
        return v

    @field_validator("edges_by_source", "edges_by_target", mode="before")
    @classmethod
    def _validate_symbol_keys(cls, v: Any) -> Any:
        if isinstance(v, dict):
            new_dict = {}
            for k, val in v.items():
                key_obj = SymbolID(value=k) if isinstance(k, str) else k
                new_dict[key_obj] = val
            return new_dict
        return v

    def get_edge(self, id: Union[EdgeID, str]) -> Optional[Edge]:
        """Fetch an Edge by its EdgeID object or string."""
        eid = EdgeID(value=id) if isinstance(id, str) else id
        return self.edges_by_id.get(eid)

    def get_outgoing_edges(self, source_symbol_id: Union[SymbolID, str]) -> List[Edge]:
        """Fetch all outgoing edges originating from a source SymbolID."""
        sid = SymbolID(value=source_symbol_id) if isinstance(source_symbol_id, str) else source_symbol_id
        eids = self.edges_by_source.get(sid, [])
        return [self.edges_by_id[eid] for eid in eids if eid in self.edges_by_id]

    def get_incoming_edges(self, target_symbol_id: Union[SymbolID, str]) -> List[Edge]:
        """Fetch all incoming edges arriving at a target SymbolID."""
        tid = SymbolID(value=target_symbol_id) if isinstance(target_symbol_id, str) else target_symbol_id
        eids = self.edges_by_target.get(tid, [])
        return [self.edges_by_id[eid] for eid in eids if eid in self.edges_by_id]

    def get_edges_by_kind(self, kind: Union[EdgeKind, str]) -> List[Edge]:
        """Fetch all relationship edges matching a specific EdgeKind."""
        ekind = EdgeKind(kind.lower()) if isinstance(kind, str) else kind
        eids = self.edges_by_kind.get(ekind, [])
        return [self.edges_by_id[eid] for eid in eids if eid in self.edges_by_id]
