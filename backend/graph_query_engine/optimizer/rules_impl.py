# backend/graph_query_engine/optimizer/rules_impl.py
"""Concrete optimization rules for the DevBrain Graph Query Engine.
Contains 13 production-quality rewrite rules operating on PhysicalPlan operators.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field

from .contracts import OptimizedPhysicalPlan
from .context import OptimizationRuleContext
from .diagnostics import AppliedRuleInfo, SkippedRuleInfo
from .metrics import OptimizationMetrics
from .result import OptimizationRuleResult
from .rules import OptimizationRule


class FilterPushdownRule(OptimizationRule):
    """Pushes filter operators down past projections, expands, or joins."""

    rule_id: str = "filter_pushdown"
    version: str = "1.0.0"
    category: str = "Filter"
    priority: int = 10

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        ops = context.physical_plan.operators
        for i in range(len(ops) - 1):
            if ops[i]["type"] in ("projection", "expand", "join") and ops[i + 1]["type"] == "filter":
                return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="Filter pushdown not applicable",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No pushdown pattern found"),
            )

        ops = [dict(op) for op in context.physical_plan.operators]
        changed = False
        i = 0
        while i < len(ops) - 1:
            if ops[i]["type"] in ("projection", "expand", "join") and ops[i + 1]["type"] == "filter":
                # Swap filter to push it down
                ops[i], ops[i + 1] = ops[i + 1], ops[i]
                changed = True
                i += 1
            else:
                i += 1

        new_plan = OptimizedPhysicalPlan(operators=ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details="Pushed filter operators down")
        metrics = OptimizationMetrics().with_increment(filter_reductions=1, depth_reduction=1)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary="Pushed filter past transform/join operators",
            applied_info=applied,
            metrics=metrics,
        )


class ProjectionPushdownRule(OptimizationRule):
    """Pushes projections down past sort or limit operators."""

    rule_id: str = "projection_pushdown"
    version: str = "1.0.0"
    category: str = "Projection"
    priority: int = 15

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        ops = context.physical_plan.operators
        for i in range(len(ops) - 1):
            if ops[i]["type"] in ("sort", "limit") and ops[i + 1]["type"] == "projection":
                return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="Projection pushdown not applicable",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No pushdown pattern found"),
            )

        ops = [dict(op) for op in context.physical_plan.operators]
        changed = False
        i = 0
        while i < len(ops) - 1:
            if ops[i]["type"] in ("sort", "limit") and ops[i + 1]["type"] == "projection":
                ops[i], ops[i + 1] = ops[i + 1], ops[i]
                changed = True
                i += 1
            else:
                i += 1

        new_plan = OptimizedPhysicalPlan(operators=ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details="Pushed projection past sort/limit operators")
        metrics = OptimizationMetrics().with_increment(projection_reductions=1)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary="Pushed projection down",
            applied_info=applied,
            metrics=metrics,
        )


class OperatorFusionRule(OptimizationRule):
    """Fuses adjacent compatible operators (e.g. adjacent filters)."""

    rule_id: str = "operator_fusion"
    version: str = "1.0.0"
    category: str = "Fusion"
    priority: int = 20

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        ops = context.physical_plan.operators
        for i in range(len(ops) - 1):
            if ops[i]["type"] == "filter" and ops[i + 1]["type"] == "filter":
                return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="Operator fusion not applicable",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No adjacent fusible operators"),
            )

        ops = [dict(op) for op in context.physical_plan.operators]
        fused_ops: List[Dict[str, Any]] = []
        i = 0
        merged_count = 0
        while i < len(ops):
            if i < len(ops) - 1 and ops[i]["type"] == "filter" and ops[i + 1]["type"] == "filter":
                p1 = ops[i].get("params", {}).get("pred", "true")
                p2 = ops[i + 1].get("params", {}).get("pred", "true")
                fused_pred = f"({p1}) AND ({p2})"
                fused_op = {
                    "type": "filter",
                    "params": {"pred": fused_pred},
                }
                fused_ops.append(fused_op)
                i += 2
                merged_count += 1
            else:
                fused_ops.append(ops[i])
                i += 1

        new_plan = OptimizedPhysicalPlan(operators=fused_ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details=f"Fused {merged_count} adjacent filters")
        metrics = OptimizationMetrics().with_increment(operators_merged=merged_count, operators_removed=merged_count)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary=f"Fused {merged_count} operator pairs",
            applied_info=applied,
            metrics=metrics,
        )


class RedundantFilterEliminationRule(OptimizationRule):
    """Eliminates filters with 'true' predicate or empty criteria."""

    rule_id: str = "redundant_filter_elimination"
    version: str = "1.0.0"
    category: str = "Filter"
    priority: int = 25

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        for op in context.physical_plan.operators:
            if op["type"] == "filter":
                pred = str(op.get("params", {}).get("pred", "")).strip().lower()
                if pred in ("true", "", "1=1"):
                    return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="No redundant filters to eliminate",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No redundant filter found"),
            )

        new_ops = []
        removed = 0
        for op in context.physical_plan.operators:
            if op["type"] == "filter":
                pred = str(op.get("params", {}).get("pred", "")).strip().lower()
                if pred in ("true", "", "1=1"):
                    removed += 1
                    continue
            new_ops.append(dict(op))

        new_plan = OptimizedPhysicalPlan(operators=new_ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details=f"Eliminated {removed} redundant filters")
        metrics = OptimizationMetrics().with_increment(operators_removed=removed, filter_reductions=removed)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary=f"Eliminated {removed} redundant filter operators",
            applied_info=applied,
            metrics=metrics,
        )


class RedundantProjectionEliminationRule(OptimizationRule):
    """Eliminates identity projections or consecutive duplicate projections."""

    rule_id: str = "redundant_projection_elimination"
    version: str = "1.0.0"
    category: str = "Projection"
    priority: int = 30

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        ops = context.physical_plan.operators
        for i, op in enumerate(ops):
            if op["type"] == "projection":
                fields = op.get("params", {}).get("fields", [])
                if fields == ["*"] or fields == "*":
                    return True
                if i < len(ops) - 1 and ops[i + 1]["type"] == "projection" and ops[i + 1].get("params") == op.get("params"):
                    return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="No redundant projections",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No redundant projections found"),
            )

        new_ops = []
        removed = 0
        ops = context.physical_plan.operators
        i = 0
        while i < len(ops):
            op = ops[i]
            if op["type"] == "projection":
                fields = op.get("params", {}).get("fields", [])
                if fields == ["*"] or fields == "*":
                    removed += 1
                    i += 1
                    continue
                if i < len(ops) - 1 and ops[i + 1]["type"] == "projection" and ops[i + 1].get("params") == op.get("params"):
                    new_ops.append(dict(op))
                    removed += 1
                    i += 2
                    continue
            new_ops.append(dict(op))
            i += 1

        new_plan = OptimizedPhysicalPlan(operators=new_ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details=f"Eliminated {removed} redundant projections")
        metrics = OptimizationMetrics().with_increment(operators_removed=removed, projection_reductions=removed)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary=f"Eliminated {removed} redundant projection operators",
            applied_info=applied,
            metrics=metrics,
        )


class ConstantFoldingRule(OptimizationRule):
    """Folds constant expressions in operator parameters."""

    rule_id: str = "constant_folding"
    version: str = "1.0.0"
    category: str = "Expression"
    priority: int = 5

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        for op in context.physical_plan.operators:
            pred = str(op.get("params", {}).get("pred", ""))
            if "1 == 1" in pred or "1 = 1" in pred or "0 == 1" in pred or "0 = 1" in pred:
                return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="No constant expressions to fold",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No foldable expressions found"),
            )

        new_ops = []
        folded = 0
        for op in context.physical_plan.operators:
            op_copy = dict(op)
            if "params" in op_copy and isinstance(op_copy["params"], dict):
                params_copy = dict(op_copy["params"])
                pred = str(params_copy.get("pred", ""))
                if "1 == 1" in pred or "1 = 1" in pred:
                    params_copy["pred"] = pred.replace("1 == 1", "true").replace("1 = 1", "true")
                    op_copy["params"] = params_copy
                    folded += 1
                elif "0 == 1" in pred or "0 = 1" in pred:
                    params_copy["pred"] = pred.replace("0 == 1", "false").replace("0 = 1", "false")
                    op_copy["params"] = params_copy
                    folded += 1
            new_ops.append(op_copy)

        new_plan = OptimizedPhysicalPlan(operators=new_ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details=f"Folded {folded} constant expressions")
        metrics = OptimizationMetrics().with_increment(estimated_complexity_reduction=1.0)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary=f"Folded {folded} constant expressions",
            applied_info=applied,
            metrics=metrics,
        )


class DeadCodeEliminationRule(OptimizationRule):
    """Removes unreachable operators following a false filter or zero limit."""

    rule_id: str = "dead_code_elimination"
    version: str = "1.0.0"
    category: str = "Cleanup"
    priority: int = 90

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        ops = context.physical_plan.operators
        for i, op in enumerate(ops):
            if op["type"] == "filter" and str(op.get("params", {}).get("pred", "")).strip().lower() in ("false", "0"):
                if i < len(ops) - 1:
                    return True
            if op["type"] == "limit" and op.get("params", {}).get("count") == 0:
                if i < len(ops) - 1:
                    return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="No dead code found",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No dead code detected"),
            )

        ops = context.physical_plan.operators
        new_ops = []
        removed = 0
        for i, op in enumerate(ops):
            new_ops.append(dict(op))
            if op["type"] == "filter" and str(op.get("params", {}).get("pred", "")).strip().lower() in ("false", "0"):
                removed = len(ops) - 1 - i
                break
            if op["type"] == "limit" and op.get("params", {}).get("count") == 0:
                removed = len(ops) - 1 - i
                break

        new_plan = OptimizedPhysicalPlan(operators=new_ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details=f"Removed {removed} dead operators")
        metrics = OptimizationMetrics().with_increment(operators_removed=removed, pipeline_reduction=1)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary=f"Eliminated {removed} unreachable operators",
            applied_info=applied,
            metrics=metrics,
        )


class JoinReorderingRule(OptimizationRule):
    """Placeholder join reordering heuristic (awaiting cost model stats)."""

    rule_id: str = "join_reordering"
    version: str = "1.0.0"
    category: str = "Join"
    priority: int = 40

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        # Currently deferred until cost model statistics are available.
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        return OptimizationRuleResult(
            optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
            changed=False,
            summary="Join reordering deferred (placeholder)",
            skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="Cost statistics unavailable"),
        )


class ExpandOptimizationRule(OptimizationRule):
    """Converts generic 'expand' operators to 'indexed_expand' if index hints exist."""

    rule_id: str = "expand_optimization"
    version: str = "1.0.0"
    category: str = "Graph"
    priority: int = 50

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        for op in context.physical_plan.operators:
            if op["type"] == "expand" and op.get("params", {}).get("index_key"):
                return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="No expand optimizations applicable",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No indexed expand candidates"),
            )

        new_ops = []
        optimized_count = 0
        for op in context.physical_plan.operators:
            if op["type"] == "expand" and op.get("params", {}).get("index_key"):
                op_copy = dict(op)
                op_copy["type"] = "indexed_expand"
                new_ops.append(op_copy)
                optimized_count += 1
            else:
                new_ops.append(dict(op))

        new_plan = OptimizedPhysicalPlan(operators=new_ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details=f"Converted {optimized_count} expand to indexed_expand")
        metrics = OptimizationMetrics().with_increment(operators_merged=0, estimated_complexity_reduction=2.0)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary=f"Converted {optimized_count} expand operators to indexed_expand",
            applied_info=applied,
            metrics=metrics,
        )


class SubqueryUnrollingRule(OptimizationRule):
    """Unrolls/inlines simple single-operator subqueries into main physical plan."""

    rule_id: str = "subquery_unrolling"
    version: str = "1.0.0"
    category: str = "Subquery"
    priority: int = 35

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        for op in context.physical_plan.operators:
            if op["type"] == "subquery" and isinstance(op.get("params", {}).get("subplan"), list):
                return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="No subqueries to unroll",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No inline subqueries found"),
            )

        new_ops = []
        unrolled = 0
        for op in context.physical_plan.operators:
            if op["type"] == "subquery" and isinstance(op.get("params", {}).get("subplan"), list):
                sub_ops = op["params"]["subplan"]
                new_ops.extend(sub_ops)
                unrolled += 1
            else:
                new_ops.append(dict(op))

        new_plan = OptimizedPhysicalPlan(operators=new_ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details=f"Unrolled {unrolled} inline subqueries")
        metrics = OptimizationMetrics().with_increment(operators_removed=unrolled, pipeline_reduction=1)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary=f"Unrolled {unrolled} inline subqueries",
            applied_info=applied,
            metrics=metrics,
        )


class LimitPushdownRule(OptimizationRule):
    """Pushes limit operators past projections to cut off work earlier."""

    rule_id: str = "limit_pushdown"
    version: str = "1.0.0"
    category: str = "Limit"
    priority: int = 18

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        ops = context.physical_plan.operators
        for i in range(len(ops) - 1):
            if ops[i]["type"] == "projection" and ops[i + 1]["type"] == "limit":
                return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="Limit pushdown not applicable",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No limit pushdown pattern found"),
            )

        ops = [dict(op) for op in context.physical_plan.operators]
        changed = False
        i = 0
        while i < len(ops) - 1:
            if ops[i]["type"] == "projection" and ops[i + 1]["type"] == "limit":
                ops[i], ops[i + 1] = ops[i + 1], ops[i]
                changed = True
                i += 1
            else:
                i += 1

        new_plan = OptimizedPhysicalPlan(operators=ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details="Pushed limit past projection")
        metrics = OptimizationMetrics().with_increment(pipeline_reduction=1)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary="Pushed limit operator down",
            applied_info=applied,
            metrics=metrics,
        )


class ScanOptimizationRule(OptimizationRule):
    """Replaces generic scan with index_scan if scan has indexed predicate."""

    rule_id: str = "scan_optimization"
    version: str = "1.0.0"
    category: str = "Scan"
    priority: int = 8

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        for op in context.physical_plan.operators:
            if op["type"] == "scan" and op.get("params", {}).get("index"):
                return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="No scan optimization applicable",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No indexed scan candidates"),
            )

        new_ops = []
        count = 0
        for op in context.physical_plan.operators:
            if op["type"] == "scan" and op.get("params", {}).get("index"):
                op_copy = dict(op)
                op_copy["type"] = "index_scan"
                new_ops.append(op_copy)
                count += 1
            else:
                new_ops.append(dict(op))

        new_plan = OptimizedPhysicalPlan(operators=new_ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details=f"Optimized {count} scan operators to index_scan")
        metrics = OptimizationMetrics().with_increment(estimated_complexity_reduction=5.0)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary=f"Converted {count} scan operators to index_scan",
            applied_info=applied,
            metrics=metrics,
        )


class IndexScanSelectionRule(OptimizationRule):
    """Selects composite_index_scan when multiple indexed fields are present."""

    rule_id: str = "index_scan_selection"
    version: str = "1.0.0"
    category: str = "Scan"
    priority: int = 9

    def can_apply(self, context: OptimizationRuleContext) -> bool:
        if not self.enabled:
            return False
        for op in context.physical_plan.operators:
            if op["type"] == "index_scan" and isinstance(op.get("params", {}).get("composite_keys"), list) and len(op["params"]["composite_keys"]) > 1:
                return True
        return False

    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        if not self.can_apply(context):
            return OptimizationRuleResult(
                optimized_plan=OptimizedPhysicalPlan(operators=context.physical_plan.operators),
                changed=False,
                summary="Index scan selection not applicable",
                skipped_info=SkippedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), reason="No composite index scan candidates"),
            )

        new_ops = []
        count = 0
        for op in context.physical_plan.operators:
            if op["type"] == "index_scan" and isinstance(op.get("params", {}).get("composite_keys"), list) and len(op["params"]["composite_keys"]) > 1:
                op_copy = dict(op)
                op_copy["type"] = "composite_index_scan"
                new_ops.append(op_copy)
                count += 1
            else:
                new_ops.append(dict(op))

        new_plan = OptimizedPhysicalPlan(operators=new_ops)
        applied = AppliedRuleInfo(name=self.rule_id, timestamp=datetime.utcnow(), details=f"Promoted {count} index_scan to composite_index_scan")
        metrics = OptimizationMetrics().with_increment(estimated_complexity_reduction=3.0)
        return OptimizationRuleResult(
            optimized_plan=new_plan,
            changed=True,
            summary=f"Promoted {count} index scans to composite_index_scan",
            applied_info=applied,
            metrics=metrics,
        )


__all__ = [
    "FilterPushdownRule",
    "ProjectionPushdownRule",
    "OperatorFusionRule",
    "RedundantFilterEliminationRule",
    "RedundantProjectionEliminationRule",
    "ConstantFoldingRule",
    "DeadCodeEliminationRule",
    "JoinReorderingRule",
    "ExpandOptimizationRule",
    "SubqueryUnrollingRule",
    "LimitPushdownRule",
    "ScanOptimizationRule",
    "IndexScanSelectionRule",
]
