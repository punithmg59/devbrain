"""Entity Resolution Orchestrator - Coordinates entity extraction and node resolution."""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .entity_extractor import EntityExtractor
from .models import EntityExtraction, RepositoryNode, ResolutionResult
from .node_resolver import NodeResolver

logger = logging.getLogger(__name__)


class EntityResolver:
    """Orchestrates the entity resolution pipeline."""

    def __init__(self):
        self.extractor = EntityExtractor()
        self.node_resolver = NodeResolver()

    async def resolve_query(
        self,
        db: AsyncSession,
        repo_id: str,
        query: str
    ) -> tuple[Optional[RepositoryNode], ResolutionResult]:
        """
        Resolve a natural language query to a repository node.

        Args:
            db: Database session
            repo_id: Repository ID
            query: Natural language query (e.g., "Delete AuthService")

        Returns:
            Tuple of (resolved node or None, resolution result)
        """
        # Step 1: Extract entities from natural language
        extraction = self.extractor.extract(query)

        if not extraction.is_valid():
            logger.warning(f"Invalid entity extraction for query: {query}")
            return None, ResolutionResult(
                node=None,
                success=False,
                match_type="none",
                suggested_matches=[],
                error_message="Could not extract engineering action and target from query"
            )

        logger.info(
            f"Extracted: action={extraction.action}, "
            f"target={extraction.target_name}, "
            f"type={extraction.target_type}, "
            f"confidence={extraction.confidence}"
        )

        # Step 2: Resolve target name against repository graph
        resolution = await self.node_resolver.resolve(
            db=db,
            repo_id=repo_id,
            target_name=extraction.target_name,
            target_type=extraction.target_type
        )

        if not resolution.success:
            logger.warning(
                f"Failed to resolve target '{extraction.target_name}': {resolution.error_message}"
            )
            return None, resolution

        logger.info(
            f"Resolved '{extraction.target_name}' to node '{resolution.node.name}' "
            f"via {resolution.match_type} match"
        )

        return resolution.node, resolution

    async def resolve_with_action(
        self,
        db: AsyncSession,
        repo_id: str,
        query: str
    ) -> tuple[Optional[RepositoryNode], Optional[str], ResolutionResult]:
        """
        Resolve a query and return both the node and the extracted action.

        Args:
            db: Database session
            repo_id: Repository ID
            query: Natural language query

        Returns:
            Tuple of (resolved node or None, action or None, resolution result)
        """
        extraction = self.extractor.extract(query)

        if not extraction.is_valid():
            return None, None, ResolutionResult(
                node=None,
                success=False,
                match_type="none",
                suggested_matches=[],
                error_message="Could not extract engineering action and target from query"
            )

        resolution = await self.node_resolver.resolve(
            db=db,
            repo_id=repo_id,
            target_name=extraction.target_name,
            target_type=extraction.target_type
        )

        if not resolution.success:
            return None, extraction.action.value if extraction.action else None, resolution

        return resolution.node, extraction.action.value if extraction.action else None, resolution
