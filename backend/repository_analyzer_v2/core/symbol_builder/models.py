"""
core/symbol_builder/models.py
------------------------------
SemanticRepository Domain Model.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from core.namespaces import NamespaceTree
from core.symbol_builder.diagnostics import PipelineDiagnostics
from core.symbol_builder.statistics import SemanticRepositoryStatistics
from core.symbol_identity import CanonicalSymbol, CanonicalSymbolCollection
from core.symbol_table import SymbolTable
from core.symbols import QualifiedName, SymbolID

SEMANTIC_REPOSITORY_VERSION = "3.6.0"


class SemanticRepository(BaseModel):
    """
    Canonical, Immutable SemanticRepository representation.
    
    Serves as the frozen semantic foundation produced by Step 3 and consumed by Step 4.
    """
    repository_id: str = Field(..., description="Repository identifier")
    workspace: Optional[Any] = Field(default=None, description="Optional Step 1 RepositoryWorkspace context")
    namespace_tree: NamespaceTree = Field(..., description="Step 3.2 NamespaceTree hierarchy")
    canonical_symbols: CanonicalSymbolCollection = Field(..., description="Step 3.4 CanonicalSymbolCollection")
    symbol_table: SymbolTable = Field(..., description="Step 3.5 Immutable SymbolTable")
    statistics: SemanticRepositoryStatistics = Field(
        default_factory=SemanticRepositoryStatistics,
        description="Aggregated pipeline statistics and timings"
    )
    diagnostics: PipelineDiagnostics = Field(
        default_factory=PipelineDiagnostics,
        description="Aggregated pipeline diagnostics report"
    )
    pipeline_metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible pipeline metadata")
    version: str = Field(default=SEMANTIC_REPOSITORY_VERSION, description="SemanticRepository schema version")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    def get_symbol(self, id: Union[SymbolID, str]) -> Optional[CanonicalSymbol]:
        """Delegate lookup to SymbolTable."""
        return self.symbol_table.get_by_symbol_id(id)

    def get_by_fqn(self, fqn: Union[str, QualifiedName]) -> Optional[CanonicalSymbol]:
        """Delegate FQN lookup to SymbolTable."""
        return self.symbol_table.get_by_qualified_name(fqn)

    def get_symbols_in_file(self, file_path: str) -> List[CanonicalSymbol]:
        """Delegate file symbols lookup to SymbolTable."""
        return self.symbol_table.get_file_symbols(file_path)

    def is_valid(self) -> bool:
        """Return True if pipeline executed with no fatal diagnostic errors."""
        return not self.diagnostics.has_errors
