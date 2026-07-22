"""pipeline/validator.py – Stage 7: graph validation."""
import logging
from pipeline.stage import PipelineContext, Stage

logger = logging.getLogger(__name__)


class ValidatorStage(Stage):
    """
    Runs integrity checks on the constructed graph (e.g. orphan nodes, cycles).
    Currently only logs execution.
    """

    @property
    def name(self) -> str:
        return "Validator"

    def setup(self, ctx: PipelineContext) -> None:
        logger.debug("[Validator] setup")

    def execute(self, ctx: PipelineContext) -> None:
        nodes = ctx.metadata.get("nodes", [])
        edges = ctx.metadata.get("edges", [])
        logger.info(
            f"[Validator] Validating graph with {len(nodes)} node(s) "
            f"and {len(edges)} edge(s) "
            f"(run_id={ctx.run_id}) – no-op stub"
        )
        # Future: detect dangling edges, duplicate node IDs, cycle detection.
        ctx.metadata["validation_passed"] = True

    def teardown(self, ctx: PipelineContext) -> None:
        logger.debug("[Validator] teardown")
