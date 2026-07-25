"""
core/dependency_graph/indexes.py
---------------------------------
Multi-dimensional fast lookup indexes for DependencyGraph.
"""

from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field

from core.edges import Edge, EdgeKind
from core.symbol_identity import CanonicalSymbol
from core.symbols import Language, SymbolKind


class DependencyGraphIndexes(BaseModel):
    """
    Immutable multi-dimensional index maps for O(1) node and edge queries across the DependencyGraph.
    """
    nodes_by_id: Dict[str, CanonicalSymbol] = Field(default_factory=dict, description="Map from SymbolID string to CanonicalSymbol")
    edges_by_id: Dict[str, Edge] = Field(default_factory=dict, description="Map from EdgeID string to Edge")
    outgoing_edges: Dict[str, List[str]] = Field(default_factory=dict, description="Map from source SymbolID string to outgoing EdgeID strings")
    incoming_edges: Dict[str, List[str]] = Field(default_factory=dict, description="Map from target SymbolID string to incoming EdgeID strings")
    edges_by_kind: Dict[EdgeKind, List[str]] = Field(default_factory=dict, description="Map from EdgeKind to EdgeID strings")
    edges_by_file: Dict[str, List[str]] = Field(default_factory=dict, description="Map from source file path to EdgeID strings")
    nodes_by_kind: Dict[SymbolKind, List[str]] = Field(default_factory=dict, description="Map from SymbolKind to SymbolID strings")
    nodes_by_file: Dict[str, List[str]] = Field(default_factory=dict, description="Map from file path to SymbolID strings")
    nodes_by_language: Dict[Language, List[str]] = Field(default_factory=dict, description="Map from Language to SymbolID strings")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }
