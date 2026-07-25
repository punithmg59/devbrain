"""
core/graph_validation/interfaces.py
------------------------------------
Public Interface Protocols for Dependency Graph Validation Framework.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.dependency_graph import IDependencyGraph


@runtime_checkable
class IDependencyGraphValidationReport(Protocol):
    """Protocol for DependencyGraphValidationReport."""
    @property
    def is_valid(self) -> bool: ...
    @property
    def repository_id(self) -> str: ...
    @property
    def validated_graph_hash(self) -> str: ...


@runtime_checkable
class IDependencyGraphValidatorFacade(Protocol):
    """Protocol for DependencyGraphValidator Facade."""
    def validate(
        self,
        dependency_graph: IDependencyGraph
    ) -> IDependencyGraphValidationReport: ...
