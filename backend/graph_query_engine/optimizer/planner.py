# backend/graph_query_engine/optimizer/planner.py
"""PlannerOptimizer high-level orchestrator for the DevBrain Graph Query Engine.
Consumes a PhysicalPlan, applies optimization passes via registry and scheduler,
validates the output, and returns an OptimizedPhysicalPlan along with an OptimizationReport.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .builder import OptimizationReportBuilder
from .contracts import PhysicalPlan, OptimizedPhysicalPlan
from .diagnostics import OptimizationDiagnostics
from .metrics import OptimizationMetrics
from .phase import OptimizationPhase
from .pipeline import OptimizationPipeline
from .registry import OptimizationRuleRegistry
from .report import OptimizationReport
from .scheduler import OptimizationScheduler
from .validation import OptimizerValidator
from .rules_impl import (
    ScanOptimizationRule,
    IndexScanSelectionRule,
    ConstantFoldingRule,
    FilterPushdownRule,
    RedundantFilterEliminationRule,
    ProjectionPushdownRule,
    RedundantProjectionEliminationRule,
    LimitPushdownRule,
    OperatorFusionRule,
    ExpandOptimizationRule,
    SubqueryUnrollingRule,
    JoinReorderingRule,
    DeadCodeEliminationRule,
)


class PlannerOptimizer:
    """High-level facade for physical plan optimization.

    Coordinates rule registry initialization, scheduler execution, output validation,
    and optimization report generation.
    """

    def __init__(
        self,
        registry: Optional[OptimizationRuleRegistry] = None,
        max_iterations: int = 10,
    ) -> None:
        self._registry = registry or self.create_default_registry()
        self._pipeline = OptimizationPipeline(registry=self._registry, max_iterations=max_iterations)
        self._scheduler = OptimizationScheduler(pipeline=self._pipeline, max_iterations=max_iterations)

    @classmethod
    def create_default_registry(cls) -> OptimizationRuleRegistry:
        """Creates and populates an OptimizationRuleRegistry with all 13 standard rules grouped by phases."""
        registry = OptimizationRuleRegistry()

        scan_phase = OptimizationPhase(
            name="Scan",
            priority=10,
            dependencies=[],
            rules=[ScanOptimizationRule(), IndexScanSelectionRule()],
        )
        expr_phase = OptimizationPhase(
            name="Expression",
            priority=20,
            dependencies=["Scan"],
            rules=[ConstantFoldingRule()],
        )
        filter_phase = OptimizationPhase(
            name="Filter",
            priority=30,
            dependencies=["Expression"],
            rules=[FilterPushdownRule(), RedundantFilterEliminationRule()],
        )
        proj_phase = OptimizationPhase(
            name="Projection",
            priority=40,
            dependencies=["Filter"],
            rules=[ProjectionPushdownRule(), RedundantProjectionEliminationRule(), LimitPushdownRule()],
        )
        fusion_phase = OptimizationPhase(
            name="Fusion",
            priority=50,
            dependencies=["Projection"],
            rules=[OperatorFusionRule()],
        )
        graph_phase = OptimizationPhase(
            name="Graph",
            priority=60,
            dependencies=["Fusion"],
            rules=[ExpandOptimizationRule(), SubqueryUnrollingRule(), JoinReorderingRule()],
        )
        cleanup_phase = OptimizationPhase(
            name="Cleanup",
            priority=90,
            dependencies=["Graph"],
            rules=[DeadCodeEliminationRule()],
        )

        for phase in (scan_phase, expr_phase, filter_phase, proj_phase, fusion_phase, graph_phase, cleanup_phase):
            registry.register_phase(phase)

        return registry

    def optimize(
        self,
        plan: PhysicalPlan,
        statistics: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> OptimizedPhysicalPlan:
        """Optimizes a PhysicalPlan and returns an OptimizedPhysicalPlan."""
        optimized_plan, _ = self.optimize_with_report(plan, statistics=statistics, config=config)
        return optimized_plan

    def optimize_with_report(
        self,
        plan: PhysicalPlan,
        statistics: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[OptimizedPhysicalPlan, OptimizationReport]:
        """Optimizes a PhysicalPlan and returns both the OptimizedPhysicalPlan and an OptimizationReport."""
        final_plan, diagnostics, metrics, _ = self._scheduler.execute(
            plan,
            statistics=statistics,
            config=config,
        )

        # Validate transformation
        OptimizerValidator.validate(plan, final_plan)

        # Build report
        report = (
            OptimizationReportBuilder()
            .before(plan)
            .after(final_plan)
            .applied_rules(diagnostics.applied)
            .skipped_rules(diagnostics.skipped)
            .rejected_rules(diagnostics.rejected)
            .metrics(metrics)
            .build()
        )

        return final_plan, report


__all__ = ["PlannerOptimizer"]
