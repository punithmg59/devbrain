"""Deterministic evidence generation for explainable risk and impact analysis."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Node
from app.services.evidence_cache import EvidenceCacheService
from app.services.evidence_explainer import EvidenceExplainer
from app.services.evidence_tree_service import EvidenceTreeService
from app.services.graph_path_service import GraphPathService
from app.services.journey_service import journey_names_for_workflows
from app.services.service_mapper import map_workflow_to_service

logger = logging.getLogger(__name__)


class EvidenceEngine:
    def __init__(self) -> None:
        self.explainer = EvidenceExplainer()
        self.tree_service = EvidenceTreeService()
        self.path_service = GraphPathService()
        self.cache_service = EvidenceCacheService()

    async def run(self, ctx, db: AsyncSession) -> None:
        if not ctx.source_node:
            ctx.evidence_chains = []
            ctx.evidence_tree = []
            ctx.evidence_summary = "No source node available for evidence generation."
            return

        cache_key = self._build_cache_key(ctx)
        cached = await self.cache_service.get_cached_evidence(
            ctx.repo_id,
            cache_key,
            db,
        )
        if cached is not None:
            ctx.evidence_chains = cached.get("chains", [])
            ctx.evidence_tree = cached.get("tree", [])
            ctx.evidence_summary = cached.get("summary", "Cached evidence available.")
            return

        chains = await self._build_evidence_chains(ctx, db)
        tree = self.tree_service.build_tree(chains, ctx.source_node.get("name"))
        summary = self._build_summary(chains)
        ctx.evidence_chains = chains
        ctx.evidence_tree = tree
        ctx.evidence_summary = summary

        await self.cache_service.set_cached_evidence(
            repo_id=ctx.repo_id,
            cache_key=cache_key,
            query=ctx.query,
            result_data={
                "chains": chains,
                "tree": tree,
                "summary": summary,
            },
            db=db,
        )

    async def _build_evidence_chains(self, ctx, db: AsyncSession) -> list[dict[str, Any]]:
        chains: list[dict[str, Any]] = []
        source_name = ctx.source_node.get("name")
        workflow_names = [w.get("workflow_name") for w in ctx.workflow_impact if w.get("workflow_name")]
        journey_names = journey_names_for_workflows(set(workflow_names))
        api_names = [n.get("route_path") or n.get("name") for n in ctx.impacted_nodes if n.get("node_type") == "api_route"]
        api_node_ids = [n["id"] for n in ctx.impacted_nodes if n.get("node_type") == "api_route"]

        for evidence in ctx.workflow_evidence:
            chains.append(
                {
                    "id": evidence.get("workflow_id"),
                    "chain_type": "workflow",
                    "target_type": "workflow",
                    "target_id": evidence.get("workflow_id", ""),
                    "summary": evidence.get("chain_summary", ""),
                    "confidence_percent": evidence.get("confidence_percent", 0.0),
                    "steps": evidence.get("steps", []),
                }
            )

        for wf in ctx.workflow_impact:
            workflow_name = wf.get("workflow_name")
            if not workflow_name:
                continue
            service_label = wf.get("service_name") or map_workflow_to_service(workflow_name)
            chain = self.explainer.build_chain(
                source_name=source_name,
                steps=[(workflow_name, "workflow")],
                target_label=service_label,
                target_type="service",
                confidence=wf.get("confidence", 0.0),
            )
            chains.append(chain)

        for journey_name in journey_names:
            chain = self.explainer.build_chain(
                source_name=source_name,
                steps=[(jn, "journey") for jn in journey_names],
                target_label=journey_name,
                target_type="journey",
                confidence=1.0,
            )
            chains.append(chain)

        for api_name in api_names[:12]:
            chain = self.explainer.build_chain(
                source_name=source_name,
                steps=[],
                target_label=api_name,
                target_type="api_route",
                confidence=0.75,
            )
            chains.append(chain)

        path = await self.path_service.shortest_path_between_nodes(
            ctx.repo_id,
            ctx.source_node.get("id"),
            api_node_ids,
            db,
        )
        if path:
            node_names = await self._node_names_by_ids(path, db)
            if node_names:
                steps = [(node_names[node_id], "node") for node_id in path[:-1] if node_id in node_names]
                target_node_name = node_names.get(path[-1], path[-1])
                chain = self.explainer.build_chain(
                    source_name=source_name,
                    steps=steps,
                    target_label=target_node_name,
                    target_type="api_route",
                    confidence=0.85,
                )
                chains.append(chain)

        return self._deduplicate_chains(chains)

    async def _node_names_by_ids(self, node_ids: list[str], db: AsyncSession) -> dict[str, str]:
        if not node_ids:
            return {}
        result = await db.execute(
            select(Node.id, Node.name).where(Node.id.in_(node_ids))
        )
        rows = result.mappings().all()
        return {str(row["id"]): row["name"] for row in rows}

    def _deduplicate_chains(self, chains: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str, str]] = set()
        unique: list[dict[str, Any]] = []
        for chain in chains:
            key = (
                chain.get("chain_type", ""),
                chain.get("target_type", ""),
                chain.get("summary", ""),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(chain)
        return unique

    def _build_cache_key(self, ctx) -> str:
        raw = f"{ctx.query}|{ctx.max_depth}|{ctx.direction}|{ctx.scenario}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def _build_summary(self, chains: list[dict[str, Any]]) -> str:
        if not chains:
            return "No evidence chains could be generated."
        return (
            f"Generated {len(chains)} deterministic evidence chains from graph, workflows, services, and journeys."
        )
