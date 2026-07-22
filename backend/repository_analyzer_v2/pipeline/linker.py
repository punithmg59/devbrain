"""pipeline/linker.py – Stage 5: dependency graph construction."""
import logging
from pipeline.stage import PipelineContext, Stage

logger = logging.getLogger(__name__)


class LinkerStage(Stage):
    """
    Resolves import references between Nodes and builds directed Edges.
    Currently only logs execution.
    """

    @property
    def name(self) -> str:
        return "Linker"

    def setup(self, ctx: PipelineContext) -> None:
        logger.debug("[Linker] setup – preparing resolution tables")

    def execute(self, ctx: PipelineContext) -> None:
        nodes = ctx.metadata.get("nodes", [])
        logger.info(
            f"[Linker] Linking {len(nodes)} node(s) into dependency graph "
            f"(run_id={ctx.run_id}) – no-op stub"
        )
        # Future: resolve qualified imports → Node ids, emit Edge objects.

    def teardown(self, ctx: PipelineContext) -> None:
        logger.debug("[Linker] teardown – clearing resolution tables")
