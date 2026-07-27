# backend/graph_query_engine/optimizer/visitor.py
"""Visitors for inspecting, comparing, validating, and visualizing physical plans and optimization reports.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Set, Union

from .contracts import PhysicalPlan, OptimizedPhysicalPlan
from .report import OptimizationReport
from .rules import OptimizationRule


class OptimizationVisitor(abc.ABC):
    """Abstract base class for all optimizer visitors."""

    @abc.abstractmethod
    def visit_plan(self, plan: Union[PhysicalPlan, OptimizedPhysicalPlan]) -> Any:
        """Visit a physical or optimized physical plan."""

    @abc.abstractmethod
    def visit_operator(self, operator: Dict[str, Any]) -> Any:
        """Visit an individual physical operator."""

    @abc.abstractmethod
    def visit_rule(self, rule: OptimizationRule) -> Any:
        """Visit an optimization rule."""

    @abc.abstractmethod
    def visit_report(self, report: OptimizationReport) -> Any:
        """Visit an optimization report."""


class RuleInspectionVisitor(OptimizationVisitor):
    """Visitor that collects information and metadata from rules."""

    def __init__(self) -> None:
        self.inspected_rules: List[Dict[str, Any]] = []

    def visit_plan(self, plan: Union[PhysicalPlan, OptimizedPhysicalPlan]) -> None:
        pass

    def visit_operator(self, operator: Dict[str, Any]) -> None:
        pass

    def visit_rule(self, rule: OptimizationRule) -> Dict[str, Any]:
        info = {
            "rule_id": rule.rule_id,
            "version": rule.version,
            "category": rule.category,
            "priority": rule.priority,
            "enabled": rule.enabled,
            "description": rule.describe(),
        }
        self.inspected_rules.append(info)
        return info

    def visit_report(self, report: OptimizationReport) -> List[Dict[str, Any]]:
        return self.inspected_rules


class PlanComparisonVisitor(OptimizationVisitor):
    """Visitor that compares a PhysicalPlan and an OptimizedPhysicalPlan to generate a diff summary."""

    def __init__(self) -> None:
        self.diff_summary: Dict[str, Any] = {}

    def visit_plan(self, plan: Union[PhysicalPlan, OptimizedPhysicalPlan]) -> None:
        pass

    def visit_operator(self, operator: Dict[str, Any]) -> None:
        pass

    def visit_rule(self, rule: OptimizationRule) -> None:
        pass

    def compare(self, before: PhysicalPlan, after: OptimizedPhysicalPlan) -> Dict[str, Any]:
        before_count = len(before.operators)
        after_count = len(after.operators)

        before_types = [op["type"] for op in before.operators]
        after_types = [op["type"] for op in after.operators]

        removed_types = [t for t in before_types if t not in after_types]
        new_types = [t for t in after_types if t not in before_types]

        self.diff_summary = {
            "before_operator_count": before_count,
            "after_operator_count": after_count,
            "operator_delta": after_count - before_count,
            "before_types": before_types,
            "after_types": after_types,
            "removed_operator_types": removed_types,
            "introduced_operator_types": new_types,
        }
        return self.diff_summary

    def visit_report(self, report: OptimizationReport) -> Dict[str, Any]:
        return self.compare(report.before_plan, report.after_plan)


class ValidationVisitor(OptimizationVisitor):
    """Visitor that traverses operators and checks integrity constraints."""

    def __init__(self) -> None:
        self.errors: List[str] = []

    def visit_plan(self, plan: Union[PhysicalPlan, OptimizedPhysicalPlan]) -> List[str]:
        if not hasattr(plan, "operators") or not isinstance(plan.operators, list):
            self.errors.append("Plan missing valid 'operators' list")
            return self.errors

        for op in plan.operators:
            self.visit_operator(op)
        return self.errors

    def visit_operator(self, operator: Dict[str, Any]) -> None:
        if not isinstance(operator, dict):
            self.errors.append(f"Invalid operator type: {type(operator)}")
            return
        if "type" not in operator:
            self.errors.append("Operator dictionary missing 'type' field")
        if not isinstance(operator.get("type"), str):
            self.errors.append("Operator 'type' field must be a string")

    def visit_rule(self, rule: OptimizationRule) -> None:
        pass

    def visit_report(self, report: OptimizationReport) -> List[str]:
        self.visit_plan(report.before_plan)
        self.visit_plan(report.after_plan)
        return self.errors


class MermaidDiagramVisitor(OptimizationVisitor):
    """Visitor that generates Mermaid markdown diagrams for optimization flow and rule dependencies."""

    def visit_plan(self, plan: Union[PhysicalPlan, OptimizedPhysicalPlan]) -> str:
        lines = ["graph TD"]
        for i, op in enumerate(plan.operators):
            node_id = f"op{i}"
            label = f"{op.get('type')}"
            lines.append(f"  {node_id}[\"{label}\"]")
            if i > 0:
                prev_id = f"op{i-1}"
                lines.append(f"  {prev_id} --> {node_id}")
        return "\n".join(lines)

    def visit_operator(self, operator: Dict[str, Any]) -> str:
        return f"operator[\"{operator.get('type')}\"]"

    def visit_rule(self, rule: OptimizationRule) -> str:
        return f"rule[\"{rule.rule_id} ({rule.category})\"]"

    def visit_report(self, report: OptimizationReport) -> str:
        lines = ["graph LR"]
        lines.append("  subgraph BeforePlan[\"Original Plan\"]")
        for i, op in enumerate(report.before_plan.operators):
            lines.append(f"    b_{i}[\"{op.get('type')}\"]")
            if i > 0:
                lines.append(f"    b_{i-1} --> b_{i}")
        lines.append("  end")

        lines.append("  subgraph AfterPlan[\"Optimized Plan\"]")
        for i, op in enumerate(report.after_plan.operators):
            lines.append(f"    a_{i}[\"{op.get('type')}\"]")
            if i > 0:
                lines.append(f"    a_{i-1} --> a_{i}")
        lines.append("  end")

        lines.append("  BeforePlan -->|\"PlannerOptimizer\"| AfterPlan")
        return "\n".join(lines)


__all__ = [
    "OptimizationVisitor",
    "RuleInspectionVisitor",
    "PlanComparisonVisitor",
    "ValidationVisitor",
    "MermaidDiagramVisitor",
]
