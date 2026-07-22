"""pipeline/reporter.py – Stage 8: result reporting."""
import logging
from pipeline.stage import PipelineContext, Stage

logger = logging.getLogger(__name__)


class ReporterStage(Stage):
    """
    Builds the final AnalysisResult summary and emits it to ctx.metadata.
    Currently only logs execution.
    """

    @property
    def name(self) -> str:
        return "Reporter"

    def setup(self, ctx: PipelineContext) -> None:
        logger.debug("[Reporter] setup")

    def execute(self, ctx: PipelineContext) -> None:
        nodes = ctx.metadata.get("nodes", [])
        edges = ctx.metadata.get("edges", [])
        errors = ctx.errors
        logger.info(
            f"[Reporter] Generating report – "
            f"{len(nodes)} node(s), {len(edges)} edge(s), "
            f"{len(errors)} error(s) "
            f"(run_id={ctx.run_id}) – no-op stub"
        )
        ctx.metadata["report"] = {
            "repository_id": ctx.repository_id,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "errors": [e.message for e in errors],
            "total_duration_ms": ctx.total_duration_ms,
            "stage_metrics": [(m.stage_name, m.duration_ms) for m in ctx.metrics],
        }

    def teardown(self, ctx: PipelineContext) -> None:
        logger.debug("[Reporter] teardown")
