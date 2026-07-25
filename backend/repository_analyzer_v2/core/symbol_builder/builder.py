"""
core/symbol_builder/builder.py
-------------------------------
SymbolBuilder Facade Entrypoint for orchestrating the complete Symbol Pipeline.
"""

from __future__ import annotations

from typing import Any, List, Optional

from core.symbol_builder.models import SemanticRepository
from core.symbol_builder.pipeline import SymbolPipelineEngine
from models.parser import ParserResult


class SymbolBuilder:
    """
    Public Facade Entrypoint for executing Step 3 Symbol Pipeline.
    """

    @classmethod
    def build(
        cls,
        workspace: Optional[Any] = None,
        parser_results: Optional[List[ParserResult]] = None,
        repository_id: Optional[str] = None
    ) -> SemanticRepository:
        """
        Orchestrate complete Symbol Pipeline:
        List[ParserResult] -> NamespaceTree -> RawSymbolCollection -> CanonicalSymbolCollection -> SymbolTable -> SemanticRepository
        """
        results = parser_results or []

        # Determine repository_id from explicit arg, workspace object, or default
        repo_id = repository_id
        if not repo_id and workspace:
            if hasattr(workspace, "repository_id") and workspace.repository_id:
                repo_id = str(workspace.repository_id)
            elif hasattr(workspace, "id") and workspace.id:
                repo_id = str(workspace.id)

        if not repo_id:
            repo_id = "repo-default"

        engine = SymbolPipelineEngine()
        return engine.execute(
            repository_id=repo_id,
            parser_results=results,
            workspace=workspace
        )
