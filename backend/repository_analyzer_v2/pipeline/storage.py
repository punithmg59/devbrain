"""pipeline/storage.py – Stage 6: persistence."""
import logging
from pipeline.stage import PipelineContext, Stage

logger = logging.getLogger(__name__)


class StorageStage(Stage):
    """
    Persists Nodes and Edges to the database / graph store.
    Currently only logs execution.
    """

    @property
    def name(self) -> str:
        return "Storage"

    def setup(self, ctx: PipelineContext) -> None:
        logger.debug("[Storage] setup – opening database connection")

    def execute(self, ctx: PipelineContext) -> None:
        nodes = ctx.metadata.get("nodes", [])
        edges = ctx.metadata.get("edges", [])
        logger.info(
            f"[Storage] Persisting {len(nodes)} node(s) and {len(edges)} edge(s) "
            f"(run_id={ctx.run_id}) – no-op stub"
        )
        # Future: upsert nodes/edges via repositories layer, update AnalysisRun status.

    def teardown(self, ctx: PipelineContext) -> None:
        logger.debug("[Storage] teardown – closing database connection")
