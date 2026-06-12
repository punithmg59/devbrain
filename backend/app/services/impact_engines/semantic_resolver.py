"""Engine 1: Smart Resolver — replaces NL resolver for Impact pipeline."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.resolver_service import SmartResolver


class SemanticResolverEngine:
    def __init__(self) -> None:
        self.resolver = SmartResolver()

    async def run(self, ctx, db: AsyncSession) -> None:
        entities, _ms, source = await self.resolver.resolve(
            ctx.query,
            ctx.repo_id,
            db,
            limit=10,
        )

        ctx.matched_entities = [
            {
                "id": e.entity_id,
                "name": e.name,
                "node_type": e.entity_type,
                "file_path": e.file_path or "",
                "match_reason": e.reason,
                "score": e.confidence / 100.0,
            }
            for e in entities
            if not e.entity_id.startswith("workflow:")
        ]

        ctx.source_node = source
        ctx.resolution_confidence = (
            entities[0].confidence / 100.0 if entities else 0.0
        )
