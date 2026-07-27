"""
Execution Pipeline & Dependency Graph Infrastructure.

Models DAG dependencies and valid topological execution ordering across ExecutionStages.
"""

from typing import Dict, List, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.execution.stage import ExecutionStage


class StageDependencyGraph(BaseModel):
    """
    Immutable DAG representation of stage dependency relationships.
    """
    model_config = ConfigDict(frozen=True)

    stage_ids: Tuple[str, ...] = Field(default_factory=tuple, description="All stage IDs in execution graph")
    dependency_edges: Dict[str, Tuple[str, ...]] = Field(
        default_factory=dict,
        description="Map of stage_id -> tuple of prerequisite stage_ids",
    )
    topological_order: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Valid topological execution order of stage IDs",
    )

    def is_acyclic(self) -> bool:
        """Verifies if the dependency graph contains zero cycles."""
        visited: Dict[str, int] = {sid: 0 for sid in self.stage_ids}  # 0=unvisited, 1=visiting, 2=visited

        def dfs(node: str) -> bool:
            visited[node] = 1
            for parent in self.dependency_edges.get(node, ()):
                if visited.get(parent, 0) == 1:
                    return False  # Cycle detected
                if visited.get(parent, 0) == 0:
                    if not dfs(parent):
                        return False
            visited[node] = 2
            return True

        for sid in self.stage_ids:
            if visited[sid] == 0:
                if not dfs(sid):
                    return False
        return True


class ExecutionPipeline(BaseModel):
    """
    Immutable execution pipeline holding ordered stages.
    """
    model_config = ConfigDict(frozen=True)

    pipeline_id: str = Field(..., description="Unique pipeline ID string")
    stages: Tuple[ExecutionStage, ...] = Field(default_factory=tuple, description="Tuple of execution stages in pipeline order")

    def count_stages(self) -> int:
        """Returns total stage count in pipeline."""
        return len(self.stages)


__all__ = [
    "StageDependencyGraph",
    "ExecutionPipeline",
]
