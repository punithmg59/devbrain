"""Workflow impact analysis for Change Intelligence pipeline."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import Workflow
from app.services.journey_service import journey_names_for_workflows
from app.services.service_mapper import map_workflow_to_service
from app.services.workflow_explainer import WorkflowExplainer
from app.services.workflow_graph_service import WorkflowGraphService

logger = logging.getLogger(__name__)

USER_IMPACT_BY_WORKFLOW: dict[str, str] = {
    "GitHub Authentication": "Users may be unable to sign in or stay logged in.",
    "Session Management": "Active sessions may invalidate; users could be logged out.",
    "Repository Connection": "Users may fail to connect or sync GitHub repositories.",
    "Repository Analysis": "Repository analysis and intelligence may degrade or fail.",
    "Impact Radar": "Change impact reports may be incomplete or misleading.",
    "Code Analysis Pipeline": "Code analysis jobs may fail or produce incomplete results.",
    "Dashboard Experience": "Dashboard may show errors or stale repository data.",
    "Public API Surface": "API clients and integrations may receive errors.",
}

SEVERITY_BY_CRITICALITY: dict[str, str] = {
    "high": "high",
    "medium": "medium",
    "low": "low",
}

RECOMMENDED_TESTS: dict[str, list[str]] = {
    "GitHub Authentication": ["OAuth Flow", "GitHub Callback", "Token Exchange"],
    "Session Management": ["Session Creation", "Session Expiry", "Auth Middleware"],
    "Repository Connection": ["Connect Repo", "GitHub Repo List", "Sync Flow"],
    "Repository Analysis": ["Full Repo Scan", "Parser Output", "Graph Build"],
}


class WorkflowImpactService:
    def __init__(self) -> None:
        self.explainer = WorkflowExplainer()
        self.graph = WorkflowGraphService()

    async def analyze(self, ctx, db: AsyncSession) -> None:
        repo_uuid = UUID(ctx.repo_id)
        workflows = await self._load_repo_workflows(repo_uuid, db)
        if not workflows:
            self._fallback_regex(ctx)
            return

        hit_ids = self._relevant_node_ids(ctx)
        matched: list[Workflow] = []
        for wf in workflows:
            wf_node_ids = {str(wn.node_id) for wn in wf.nodes}
            if wf_node_ids & hit_ids:
                matched.append(wf)

        if not matched and ctx.source_node:
            matched = self._match_by_name(ctx, workflows)

        if not matched:
            self._fallback_regex(ctx)
            return

        matched.sort(key=lambda w: w.confidence, reverse=True)
        primary = matched[0]

        workflow_impacts: list[dict] = []
        service_names: set[str] = set()
        journey_names: set[str] = set()
        all_evidence: list[dict] = []

        for wf in matched[:6]:
            svc = (
                wf.services[0].service_name
                if wf.services
                else map_workflow_to_service(wf.name)
            )
            service_names.add(svc)
            journey_names.update(journey_names_for_workflows({wf.name}))

            node_names = await self.explainer.ordered_nodes_in_workflow(
                str(wf.id), ctx.repo_id, db
            )
            evidence_nodes = [
                n
                for n in node_names
                if any(
                    n == hit.get("name")
                    for hit in ([ctx.source_node] if ctx.source_node else [])
                    + ctx.impacted_nodes
                )
            ][:5]
            if not evidence_nodes and ctx.source_node:
                evidence_nodes = [ctx.source_node.get("name", "")]
            if not evidence_nodes:
                evidence_nodes = node_names[:4]

            chain = self.explainer.build_chain(
                source_node=ctx.source_node,
                impacted_node_names=evidence_nodes,
                workflow_name=wf.name,
                workflow_confidence=wf.confidence,
            )
            all_evidence.append(
                {
                    "workflow_id": str(wf.id),
                    "workflow_name": wf.name,
                    "chain_summary": chain.summary,
                    "confidence_percent": chain.confidence,
                    "steps": [s.model_dump() for s in chain.steps],
                }
            )

            apis = [a.api_route for a in wf.apis[:8]]
            workflow_impacts.append(
                {
                    "workflow_id": str(wf.id),
                    "workflow_name": wf.name,
                    "user_impact": USER_IMPACT_BY_WORKFLOW.get(
                        wf.name,
                        f"The {wf.name} workflow may experience errors or degraded behavior.",
                    ),
                    "evidence_nodes": evidence_nodes,
                    "evidence_source": "workflow_db",
                    "service_name": svc,
                    "severity": SEVERITY_BY_CRITICALITY.get(wf.criticality, "medium"),
                    "confidence": wf.confidence,
                    "confidence_percent": round(wf.confidence * 100, 1),
                    "evidence_chain": chain.summary,
                    "affected_apis": apis,
                    "recommended_tests": RECOMMENDED_TESTS.get(wf.name, []),
                    "criticality": wf.criticality,
                }
            )

        ctx.workflow_impact = workflow_impacts
        ctx.primary_workflow = {
            "id": str(primary.id),
            "name": primary.name,
            "confidence": primary.confidence,
            "confidence_percent": round(primary.confidence * 100, 1),
            "service_name": (
                primary.services[0].service_name
                if primary.services
                else map_workflow_to_service(primary.name)
            ),
        }
        ctx.affected_services = sorted(service_names)
        ctx.affected_journeys = sorted(journey_names)
        ctx.workflow_evidence = all_evidence
        ctx.workflow_confidence = primary.confidence

        ctx.user_impact = list(
            dict.fromkeys(w["user_impact"] for w in workflow_impacts)
        )[:6]
        ctx.business_impact = [
            self._business_line(w["workflow_name"], ctx.scenario) for w in workflow_impacts
        ][:6]
        ctx.engineering_impact = self._engineering_lines(ctx, workflow_impacts)

        related = await self.graph.related_workflow_names(primary, repo_uuid, db)
        ctx.workflow_graph_chain = self.graph.workflow_chain_for_names(
            [w.name for w in matched] + related
        )

    async def _load_repo_workflows(
        self, repo_id: UUID, db: AsyncSession
    ) -> list[Workflow]:
        result = await db.execute(
            select(Workflow)
            .where(Workflow.repo_id == repo_id)
            .options(
                selectinload(Workflow.nodes),
                selectinload(Workflow.apis),
                selectinload(Workflow.services),
            )
        )
        return list(result.scalars().all())

    def _relevant_node_ids(self, ctx) -> set[str]:
        ids: set[str] = set()
        if ctx.source_node and ctx.source_node.get("id"):
            ids.add(str(ctx.source_node["id"]))
        for n in ctx.impacted_nodes:
            if n.get("id"):
                ids.add(str(n["id"]))
        return ids

    def _match_by_name(self, ctx, workflows: list[Workflow]) -> list[Workflow]:
        from app.services.workflow_discovery_service import WORKFLOW_SEEDS

        if not ctx.source_node:
            return []
        blob = (
            f"{ctx.source_node.get('name', '')} "
            f"{ctx.source_node.get('file_path', '')} "
            f"{ctx.query}"
        )
        seed_by_name = {s.name: s for s in WORKFLOW_SEEDS}
        out: list[Workflow] = []
        for wf in workflows:
            seed = seed_by_name.get(wf.name)
            if seed and seed.node_patterns.search(blob):
                out.append(wf)
        return out

    def _fallback_regex(self, ctx) -> None:
        from app.services.workflow_regex_fallback import apply_regex_workflow_impact

        apply_regex_workflow_impact(ctx)

    def _business_line(self, workflow_name: str, scenario: str) -> str:
        if scenario == "delete":
            return f"{workflow_name} may break entirely if this component is removed."
        return f"{workflow_name} may experience errors or degraded reliability."

    def _engineering_lines(self, ctx, workflow_impacts: list[dict]) -> list[str]:
        lines: list[str] = []
        if ctx.apis:
            lines.append(
                f"Regression required on {len(ctx.apis)} verified API route(s) in blast radius."
            )
        for w in workflow_impacts[:3]:
            if w.get("affected_apis"):
                lines.append(
                    f"{w['workflow_name']}: verify {', '.join(w['affected_apis'][:3])}"
                )
        if ctx.scenario == "delete":
            lines.insert(
                0,
                "Deletion removes a node with active incoming edges — breaking change confirmed.",
            )
        return list(dict.fromkeys(lines))[:8]
