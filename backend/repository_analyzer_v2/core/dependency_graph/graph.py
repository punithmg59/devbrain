"""
core/dependency_graph/graph.py
-------------------------------
Immutable DependencyGraph Domain Model.
"""

from __future__ import annotations

from typing import List, Optional, Union
from pydantic import BaseModel, Field

from core.dependency_graph.diagnostics import DependencyGraphDiagnostics
from core.dependency_graph.indexes import DependencyGraphIndexes
from core.dependency_graph.statistics import DependencyGraphStatistics
from core.edges import Edge, EdgeID, EdgeKind
from core.symbol_identity import CanonicalSymbol, CanonicalSymbolCollection
from core.symbol_table import SymbolTable
from core.symbols import SymbolID


class DependencyGraph(BaseModel):
    """
    Immutable unified Dependency Graph representing all symbols, namespaces, and relationship edges.
    """
    repository_id: str = Field(..., description="Repository identifier")
    canonical_symbols: CanonicalSymbolCollection = Field(..., description="Complete collection of canonical symbols")
    symbol_table: SymbolTable = Field(..., description="Multi-dimensional SymbolTable index from Step 3.5")
    edges: List[Edge] = Field(..., description="Deduplicated list of canonical relationship edges")
    indexes: DependencyGraphIndexes = Field(..., description="Multi-dimensional fast graph lookup maps")
    statistics: DependencyGraphStatistics = Field(..., description="Graph metrics and density statistics")
    diagnostics: DependencyGraphDiagnostics = Field(..., description="Aggregated pipeline diagnostics")
    version: str = Field(default="4.6.0", description="DependencyGraph schema semver")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    def get_symbol(self, symbol_id: Union[SymbolID, str]) -> Optional[CanonicalSymbol]:
        """Fetch canonical symbol by SymbolID in O(1) time."""
        key = symbol_id.value if isinstance(symbol_id, SymbolID) else str(symbol_id)
        return self.indexes.nodes_by_id.get(key)

    def get_edge(self, edge_id: Union[EdgeID, str]) -> Optional[Edge]:
        """Fetch canonical edge by EdgeID in O(1) time."""
        key = edge_id.value if isinstance(edge_id, EdgeID) else str(edge_id)
        return self.indexes.edges_by_id.get(key)

    def get_outgoing_edges(self, symbol_id: Union[SymbolID, str]) -> List[Edge]:
        """Fetch all outgoing relationship edges for a given symbol in O(1) time."""
        key = symbol_id.value if isinstance(symbol_id, SymbolID) else str(symbol_id)
        edge_ids = self.indexes.outgoing_edges.get(key, [])
        return [self.indexes.edges_by_id[eid] for eid in edge_ids if eid in self.indexes.edges_by_id]

    def get_incoming_edges(self, symbol_id: Union[SymbolID, str]) -> List[Edge]:
        """Fetch all incoming relationship edges for a given symbol in O(1) time."""
        key = symbol_id.value if isinstance(symbol_id, SymbolID) else str(symbol_id)
        edge_ids = self.indexes.incoming_edges.get(key, [])
        return [self.indexes.edges_by_id[eid] for eid in edge_ids if eid in self.indexes.edges_by_id]

    def get_edges_by_kind(self, kind: Union[EdgeKind, str]) -> List[Edge]:
        """Fetch all relationship edges of a specific EdgeKind in O(1) time."""
        key = kind.value if isinstance(kind, EdgeKind) else str(kind)
        edge_ids = self.indexes.edges_by_kind.get(key, [])
        return [self.indexes.edges_by_id[eid] for eid in edge_ids if eid in self.indexes.edges_by_id]

    def get_file_nodes(self, file_path: str) -> List[CanonicalSymbol]:
        """Fetch all canonical symbols declared within a specific file in O(1) time."""
        sym_ids = self.indexes.nodes_by_file.get(file_path, [])
        return [self.indexes.nodes_by_id[sid] for sid in sym_ids if sid in self.indexes.nodes_by_id]
