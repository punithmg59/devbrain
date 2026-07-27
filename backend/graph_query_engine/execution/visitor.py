"""
Generic Visitor Pattern Infrastructure for Execution Plan Traversal.
"""

from typing import Any, List, Protocol, runtime_checkable
from graph_query_engine.execution.operators import ExecutionOperator
from graph_query_engine.execution.plan import ExecutionPlan
from graph_query_engine.execution.stage import ExecutionStage


@runtime_checkable
class ExecutionVisitor(Protocol):
    """Protocol for Execution Plan Visitors."""

    def visit_execution_plan(self, plan: ExecutionPlan) -> Any:
        """Visits ExecutionPlan root container."""
        ...

    def visit_execution_stage(self, stage: ExecutionStage) -> Any:
        """Visits an ExecutionStage container."""
        ...

    def visit_execution_operator(self, operator: ExecutionOperator) -> Any:
        """Visits an individual ExecutionOperator instance."""
        ...


class BaseExecutionVisitor:
    """
    Abstract base class providing default pipeline stage traversal of Execution Plans.
    """

    def visit_execution_plan(self, plan: ExecutionPlan) -> Any:
        """Visits ExecutionPlan and dispatches to all stages."""
        results = []
        for stage in plan.stages:
            results.append(stage.accept(self))
        return results

    def visit_execution_stage(self, stage: ExecutionStage) -> Any:
        """Visits ExecutionStage and all its inner operators."""
        results = []
        for op in stage.operators:
            results.append(op.accept(self))
        return results

    def visit_execution_operator(self, operator: ExecutionOperator) -> Any:
        """Default handler for ExecutionOperator."""
        return operator.operator_name


class PrintExecutionVisitor(BaseExecutionVisitor):
    """
    Visitor formatting a text tree representation of an ExecutionPlan and its stage DAG dependencies.
    """

    def __init__(self) -> None:
        self._lines: List[str] = []

    def print_plan(self, target: Any) -> str:
        """Renders formatted text tree for ExecutionPlan or ExecutionStage."""
        self._lines.clear()
        if hasattr(target, "accept"):
            target.accept(self)
        else:
            self.visit_execution_plan(target)
        return "\n".join(self._lines)

    def visit_execution_stage(self, stage: ExecutionStage) -> Any:
        deps_str = f" (depends_on={stage.dependencies})" if stage.dependencies else ""
        self._lines.append(f"Stage[{stage.stage_id}] -> {stage.stage_type}{deps_str}")
        for op in stage.operators:
            self._lines.append(f"  - ExecOp({op.execution_operator_id}): {op.operator_name}")
        return super().visit_execution_stage(stage)


class ValidationExecutionVisitor(BaseExecutionVisitor):
    """Visitor collecting execution stage self-validation errors."""

    def __init__(self) -> None:
        self.errors: List[str] = []

    def validate(self, target: Any) -> List[str]:
        """Executes validation traversal returning error messages list."""
        self.errors.clear()
        if hasattr(target, "accept"):
            target.accept(self)
        else:
            self.visit_execution_plan(target)
        return list(self.errors)

    def visit_execution_stage(self, stage: ExecutionStage) -> Any:
        self.errors.extend(stage.validate_stage())
        return super().visit_execution_stage(stage)


__all__ = [
    "ExecutionVisitor",
    "BaseExecutionVisitor",
    "PrintExecutionVisitor",
    "ValidationExecutionVisitor",
]
