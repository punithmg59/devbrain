"""
Generic Visitor Pattern Infrastructure for Physical Plan Traversal.
"""

from typing import Any, List, Protocol, runtime_checkable
from graph_query_engine.physical.operators import PhysicalOperator
from graph_query_engine.physical.plan import PhysicalPlan, PhysicalPlanNode


@runtime_checkable
class PhysicalVisitor(Protocol):
    """Protocol for Physical Plan Visitors."""

    def visit_physical_plan(self, plan: PhysicalPlan) -> Any:
        """Visits PhysicalPlan root container."""
        ...

    def visit_physical_plan_node(self, node: PhysicalPlanNode) -> Any:
        """Visits PhysicalPlanNode tree node."""
        ...

    def visit_physical_operator(self, operator: PhysicalOperator) -> Any:
        """Visits an individual PhysicalOperator instance."""
        ...


class BasePhysicalVisitor:
    """
    Abstract base class providing default depth-first traversal of Physical Plans.
    """

    def visit_physical_plan(self, plan: PhysicalPlan) -> Any:
        """Visits PhysicalPlan and dispatches to root_node."""
        return plan.root_node.accept(self)

    def visit_physical_plan_node(self, node: PhysicalPlanNode) -> Any:
        """Visits PhysicalPlanNode, its operator content, and child nodes."""
        results = [node.operator.accept(self)]
        for child in node.children:
            results.append(child.accept(self))
        return results

    def visit_physical_operator(self, operator: PhysicalOperator) -> Any:
        """Default handler for PhysicalOperator."""
        return operator.operator_name


class PrintPhysicalVisitor(BasePhysicalVisitor):
    """
    Visitor formatting a text tree representation of a PhysicalPlan and its execution strategies.
    """

    def __init__(self) -> None:
        self._lines: List[str] = []
        self._indent: int = 0

    def print_plan(self, target: Any) -> str:
        """Renders formatted text tree for PhysicalPlan or PhysicalPlanNode."""
        self._lines.clear()
        self._indent = 0
        if hasattr(target, "accept"):
            target.accept(self)
        else:
            self.visit_physical_plan(target)
        return "\n".join(self._lines)

    def visit_physical_plan_node(self, node: PhysicalPlanNode) -> Any:
        prefix = "  " * self._indent
        op = node.operator
        self._lines.append(f"{prefix}- PhysicalNode({node.node_id}) -> {op.operator_name}(id={op.operator_id})")
        self._indent += 1
        super().visit_physical_plan_node(node)
        self._indent -= 1


class ValidationPhysicalVisitor(BasePhysicalVisitor):
    """Visitor collecting physical operator self-validation errors."""

    def __init__(self) -> None:
        self.errors: List[str] = []

    def validate(self, target: Any) -> List[str]:
        """Executes validation traversal returning error messages list."""
        self.errors.clear()
        if hasattr(target, "accept"):
            target.accept(self)
        else:
            self.visit_physical_plan(target)
        return list(self.errors)

    def visit_physical_plan_node(self, node: PhysicalPlanNode) -> Any:
        self.errors.extend(node.operator.validate_operator())
        return super().visit_physical_plan_node(node)


__all__ = [
    "PhysicalVisitor",
    "BasePhysicalVisitor",
    "PrintPhysicalVisitor",
    "ValidationPhysicalVisitor",
]
