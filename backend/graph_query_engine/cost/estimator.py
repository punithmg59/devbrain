"""
Main Cost Estimator Subsystem Orchestrator.

Consumes an immutable LogicalPlan → Produces an immutable CostReport.
NEVER mutates LogicalPlan, NEVER accesses GraphView, NEVER executes queries.
"""

from typing import Dict, Optional
from graph_query_engine.cost.aggregator import CostAggregator
from graph_query_engine.cost.diagnostics import CostDiagnostics
from graph_query_engine.cost.estimate import CostEstimate, CostReport
from graph_query_engine.cost.statistics import GraphStatisticsMetadata
from graph_query_engine.cost.validation import CostValidator
from graph_query_engine.cost.visitor import BaseCostVisitor
from graph_query_engine.logical.plan import LogicalPlan


class CostEstimator:
    """
    Main Cost Model Analysis Pass Orchestrator.

    Calculates deterministic, explainable, immutable cost estimates for a LogicalPlan.
    """

    def __init__(self, default_stats: Optional[GraphStatisticsMetadata] = None) -> None:
        self.default_stats = default_stats or GraphStatisticsMetadata()

    def estimate_plan_cost(
        self,
        plan: LogicalPlan,
        stats: Optional[GraphStatisticsMetadata] = None,
    ) -> CostReport:
        """
        Calculates operator and total plan cost estimates for a LogicalPlan.
        """
        active_stats = stats or self.default_stats
        diagnostics = CostDiagnostics()

        diagnostics.record_trace(f"Initiating Cost Model estimation for LogicalPlan '{plan.plan_id}'")

        # 1. Run BaseCostVisitor to compute bottom-up operator cost breakdowns
        visitor = BaseCostVisitor(stats=active_stats)
        operator_breakdowns = visitor.visit_plan(plan)

        for b in operator_breakdowns:
            diagnostics.record_trace(
                f"Operator '{b.operator_id}' ({b.operator_name}): cost={b.estimate.estimated_operator_cost:.2f}, card={b.estimate.estimated_cardinality:.1f}",
                operator_id=b.operator_id,
            )

        # 2. Aggregate per-operator estimates into total plan cost
        total_estimate = CostAggregator.aggregate_plan_cost(operator_breakdowns)

        # 3. Build confidence and statistics summary
        confidence_report: Dict[str, float] = {
            b.operator_id: b.estimate.confidence_score for b in operator_breakdowns
        }
        stats_summary: Dict[str, float] = {
            "total_node_count": float(active_stats.nodes.total_node_count),
            "total_edge_count": float(active_stats.edges.total_edge_count),
            "average_degree": active_stats.edges.average_degree,
        }

        # 4. Construct preliminary report and validate
        report = CostReport(
            plan_id=plan.plan_id,
            query_id=plan.query_id,
            total_cost_estimate=total_estimate,
            operator_costs=operator_breakdowns,
            diagnostics=diagnostics.get_traces(),
            warnings=diagnostics.get_warnings(),
            confidence_report=confidence_report,
            statistics_summary=stats_summary,
        )

        val_report = CostValidator.validate_report(report)
        if not val_report.is_valid:
            err_msg = "; ".join(v.message for v in val_report.violations if v.severity == "ERROR")
            diagnostics.record_warning(f"CostReport validation warning: {err_msg}")

        return CostReport(
            report_id=report.report_id,
            plan_id=report.plan_id,
            query_id=report.query_id,
            created_at=report.created_at,
            total_cost_estimate=report.total_cost_estimate,
            operator_costs=report.operator_costs,
            diagnostics=diagnostics.get_traces(),
            warnings=diagnostics.get_warnings(),
            confidence_report=report.confidence_report,
            statistics_summary=report.statistics_summary,
        )


__all__ = ["CostEstimator"]
