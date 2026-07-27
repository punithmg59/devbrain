"""
Generic Visitor Pattern Infrastructure for Logical Plan Traversal.
"""

from typing import Any, List, Protocol, runtime_checkable

from graph_query_engine.logical.operators import LogicalOperator
from graph_query_engine.logical.plan import LogicalPlan, LogicalPlanNode


@runtime_checkable
class LogicalVisitor(Protocol):
    """
    Protocol definition for Logical Plan Visitors.
    """

    def visit_plan(self, plan: LogicalPlan) -> Any:
        """Visits LogicalPlan root container."""
        ...

    def visit_plan_node(self, node: LogicalPlanNode) -> Any:
        """Visits LogicalPlanNode tree node."""
        ...

    def visit_operator(self, operator: LogicalOperator) -> Any:
        """Visits an individual LogicalOperator instance."""
        ...


class BaseLogicalVisitor:
    """
    Abstract base class providing default depth-first traversal of Logical Plans.
    """

    def visit_plan(self, plan: LogicalPlan) -> Any:
        """Visits LogicalPlan and dispatches to root_node."""
        return plan.root_node.accept(self)

    def visit_plan_node(self, node: LogicalPlanNode) -> Any:
        """Visits LogicalPlanNode, its operator content, and child nodes."""
        results = [node.operator.accept(self)]
        for child in node.children:
            results.append(child.accept(self))
        return results

    def visit_operator(self, operator: LogicalOperator) -> Any:
        """Default handler for LogicalOperator."""
        return operator.operator_name


class PrintLogicalVisitor(BaseLogicalVisitor):
    """
    Visitor that formats and renders a human-readable text tree representation of a LogicalPlan.
    """

    def __init__(self) -> None:
        self._lines: List[str] = []
        self._indent: int = 0

    def print_plan(self, target: Any) -> str:
        """Renders string representation of target (LogicalPlan or LogicalPlanNode)."""
        self._lines.clear()
        self._indent = 0
        if hasattr(target, "accept"):
            target.accept(self)
        else:
            self.visit_plan(target)
        return "\n".join(self._lines)

    def visit_plan_node(self, node: LogicalPlanNode) -> Any:
        prefix = "  " * self._indent
        op_info = f"{node.operator.operator_name}(id={node.operator.operator_id})"
        self._lines.append(f"{prefix}- LogicalNode({node.node_id}) -> {op_info}")
        self._indent += 1
        super().visit_plan_node(node)
        self._indent -= 1


class ValidationLogicalVisitor(BaseLogicalVisitor):
    """
    Visitor collecting operator self-validation errors across plan nodes.
    """

    def __init__(self) -> None:
        self.errors: List[str] = []

    def validate(self, target: Any) -> List[str]:
        """Executes validation traversal returning error messages list."""
        self.errors.clear()
        if hasattr(target, "accept"):
            target.accept(self)
        else:
            self.visit_plan(target)
        return list(self.errors)

    def visit_plan_node(self, node: LogicalPlanNode) -> Any:
        errs = node.operator.validate_operator()
        self.errors.extend(errs)
        return super().visit_plan_node(node)


__all__ = [
    "LogicalVisitor",
    "BaseLogicalVisitor",
    "PrintLogicalVisitor",
    "ValidationLogicalVisitor",
]
