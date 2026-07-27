# backend/graph_query_engine/traversal/pipeline.py
"""TraversalPipeline composes and executes sequential sequences of TraversalOperators.
"""

from __future__ import annotations

import time
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from .context import TraversalExecutionContext
from .operators.base import TraversalOperator
from .result import TraversalResult
from .operators.transform import TraversalResultBuilderOperator


class TraversalPipeline(BaseModel):
    """Pipeline of composable traversal operators."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    operators: List[TraversalOperator] = Field(default_factory=list)

    def execute(
        self,
        context: TraversalExecutionContext,
        start_nodes: List[str],
    ) -> TraversalResult:
        start_time = time.perf_counter()
        current_nodes = list(start_nodes)

        for op in self.operators:
            current_nodes = op.execute(context, current_nodes)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        builder_op = TraversalResultBuilderOperator(root_nodes=start_nodes)
        return builder_op.build_result(context, current_nodes, elapsed_ms=elapsed_ms)


__all__ = ["TraversalPipeline"]
