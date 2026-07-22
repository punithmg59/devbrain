"""pipeline/extractor.py – Stage 4: entity & symbol extraction."""
import logging
from pipeline.stage import PipelineContext, Stage

logger = logging.getLogger(__name__)


class ExtractorStage(Stage):
    """
    Extracts Nodes, Symbols, Imports, Exports and Routes from parsed ASTs.
    Currently only logs execution.
    """

    @property
    def name(self) -> str:
        return "Extractor"

    def setup(self, ctx: PipelineContext) -> None:
        logger.debug("[Extractor] setup")

    def execute(self, ctx: PipelineContext) -> None:
        asts = ctx.metadata.get("parsed_asts", {})
        logger.info(
            f"[Extractor] Extracting entities from {len(asts)} AST(s) "
            f"(run_id={ctx.run_id}) – no-op stub"
        )
        # Future: call plugin.extract_entities / extract_symbols / extract_imports …
        ctx.metadata["nodes"] = []
        ctx.metadata["edges"] = []

    def teardown(self, ctx: PipelineContext) -> None:
        logger.debug("[Extractor] teardown")
