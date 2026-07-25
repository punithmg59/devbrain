"""
core/facade/interfaces.py
--------------------------
Public Interface Protocols for DependencyGraph Facade.
"""

from __future__ import annotations

from typing import Any, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class IRepositoryAnalysisResult(Protocol):
    """Protocol for RepositoryAnalysisResult."""
    @property
    def repository_id(self) -> str: ...
    @property
    def version(self) -> str: ...


@runtime_checkable
class IDependencyGraphFacade(Protocol):
    """Protocol for DependencyGraphFacade."""
    def analyze_repository(
        self,
        parser_results: List[Any],
        repository_id: str,
        workspace: Optional[Any] = None
    ) -> IRepositoryAnalysisResult: ...
