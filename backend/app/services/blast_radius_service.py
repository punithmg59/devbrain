"""
Blast Radius Intelligence Engine — deterministic graph analysis at scale.
Uses SQL CTE traversal, DB cache, and precomputed metrics. No LLM.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.business_impact_service import BusinessImpactService
from app.services.centrality_service import CentralityService
from app.services.critical_path_service import CriticalPathService
from app.services.journey_impact_service import JourneyImpactService
from app.services.service_mapper import map_workflow_to_service

logger = logging.getLogger(__name__)

CACHE_TTL_HOURS = 24

SCORE_WEIGHTS = {
    "dependency_reach": 30,
    "workflow_reach": 20,
    "service_reach": 20,
    "api_reach": 10,
    "critical_path_reach": 20,
}


def category_from_score(score: int) -> str:
    if score <= 20:
        return "safe"
    if score <= 40:
        return "low"
    if score <= 60:
        return "medium"
    if score <= 80:
        return "high"
    return "critical"


def users_impacted_tier(score: int, journey_count: int) -> str:
    if score >= 61 or journey_count >= 2:
        return "HIGH"
    if score >= 41 or journey_count >= 1:
        return "MEDIUM"
    return "LOW"


class BlastRadiusEngine:
    def __init__(self) -> None:
        self.centrality = CentralityService()
        self.critical_paths = CriticalPathService()
        self.journey_impact = JourneyImpactService()
        self.business_impact = BusinessImpactService()

    async def calculate(self, ctx, db: AsyncSession) -> dict:
        """Full blast radius report; mutates ctx.blast_radius and related fields."""
        if not ctx.source_node:
            return self._empty_report(ctx)

        direction = self._effective_direction(ctx)
        depth = min(10, max(1, ctx.max_depth))

        cached = await self._read_cache(
            ctx.repo_id, ctx.source_node["id"], direction, depth, db
        )
        if cached:
            self._apply_report_to_ctx(ctx, cached)
            return cached

        node_ids = self._node_id_set(ctx)
        dimensions = await self._gather_dimensions(ctx, node_ids, db)
        paths = await self.critical_paths.list_paths(UUID(ctx.repo_id), db)
        critical_hit = self.critical_paths.paths_impacted(
            paths, node_ids, ctx.source_node.get("id")
        )
        dimensions["critical_paths_impacted"] = critical_hit
        dimensions["critical_paths_count"] = len(critical_hit)

        score, breakdown = self.calculate_blast_radius_score(dimensions)
        category = category_from_score(score)
        users_tier = users_impacted_tier(
            score, dimensions.get("journeys_impacted", 0)
        )

        wf_names = set(dimensions.get("workflow_names", []))
        journey_impacts = self.journey_impact.analyze(wf_names)
        business_impacts = self.business_impact.analyze(journey_impacts)

        report = {
            **dimensions,
            "blast_radius_score": score,
            "risk_category": category,
            "score_breakdown": breakdown,
            "estimated_users_impacted": users_tier,
            "deployment_risk": category if category in ("high", "critical") else "medium"
            if score > 40
            else "low",
            "critical_paths_impacted": critical_hit,
            "journey_impacts": journey_impacts,
            "business_impacts": business_impacts,
            "summary": self.generate_summary(dimensions, score, category, critical_hit),
            "direction": direction,
            "depth": depth,
            "scenario": ctx.scenario,
        }

        await self._write_cache(
            ctx.repo_id, ctx.source_node["id"], direction, depth, report, db
        )
        self._apply_report_to_ctx(ctx, report)
        return report

    def _effective_direction(self, ctx) -> str:
        if ctx.scenario == "delete":
            return "upstream"
        if ctx.scenario == "refactor" and ctx.direction == "both":
            return "downstream"
        return ctx.direction if ctx.direction in ("upstream", "downstream") else "both"

    def _node_id_set(self, ctx) -> set[str]:
        ids = {n["id"] for n in ctx.impacted_nodes}
        if ctx.source_node and ctx.source_node.get("id"):
            ids.add(str(ctx.source_node["id"]))
        return ids

    async def _gather_dimensions(
        self, ctx, node_ids: set[str], db: AsyncSession
    ) -> dict:
        nodes = [ctx.source_node, *ctx.impacted_nodes] if ctx.source_node else ctx.impacted_nodes
        functions = sum(
            1 for n in nodes if n and n.get("node_type") in ("function", "method")
        )
        classes = sum(1 for n in nodes if n and n.get("node_type") == "class")
        apis = [
            n
            for n in nodes
            if n
            and (n.get("node_type") == "api_route" or n.get("route_path"))
        ]
        files = {n.get("file_path") for n in nodes if n and n.get("file_path")}

        wf_data = await self.find_impacted_workflows(ctx.repo_id, node_ids, db)
        services = await self.find_impacted_services(wf_data)
        journeys = await self.find_impacted_journeys(wf_data)

        centrality_scores = await self.centrality.load_scores_for_nodes(
            UUID(ctx.repo_id), list(node_ids), db
        )
        source_centrality = None
        if ctx.source_node:
            source_centrality = centrality_scores.get(str(ctx.source_node["id"]))

        return {
            "functions_impacted": functions,
            "classes_impacted": classes,
            "files_impacted": len(files),
            "apis_impacted": len(apis),
            "workflows_impacted": len(wf_data),
            "services_impacted": len(services),
            "journeys_impacted": len(journeys),
            "total_nodes": len(ctx.impacted_nodes),
            "verified_edges": len(ctx.graph_edges),
            "max_depth": max((n.get("depth", 0) for n in ctx.impacted_nodes), default=0),
            "workflow_names": [w["name"] for w in wf_data],
            "service_names": services,
            "journey_names": journeys,
            "api_routes": [
                f"{a.get('http_method') or 'GET'} {a.get('route_path') or a.get('name')}"
                for a in apis
            ],
            "source_centrality_score": source_centrality,
            "functions": functions,
            "classes": classes,
            "api_routes_count": len(apis),
            "files": len(files),
        }

    async def find_impacted_workflows(
        self, repo_id: str, node_ids: set[str], db: AsyncSession
    ) -> list[dict]:
        if not node_ids:
            return []
        uuids = [UUID(n) for n in node_ids]
        rows = (
            await db.execute(
                text("""
                    SELECT DISTINCT w.id, w.name, w.criticality, w.confidence
                    FROM workflows w
                    JOIN workflow_nodes wn ON wn.workflow_id = w.id
                    WHERE w.repo_id = :repo_id AND wn.node_id = ANY(:ids)
                """),
                {"repo_id": repo_id, "ids": uuids},
            )
        ).mappings()
        return [dict(r) for r in rows]

    async def find_impacted_services(self, workflows: list[dict]) -> list[str]:
        names: set[str] = set()
        for wf in workflows:
            names.add(map_workflow_to_service(wf["name"]))
        return sorted(names)

    async def find_impacted_journeys(self, workflows: list[dict]) -> list[str]:
        from app.services.journey_service import journey_names_for_workflows

        wf_names = {w["name"] for w in workflows}
        return journey_names_for_workflows(wf_names)

    def find_impacted_nodes(self, ctx) -> list[dict]:
        return ctx.impacted_nodes

    def find_impacted_files(self, ctx) -> list[str]:
        return list({n.get("file_path") for n in ctx.impacted_nodes if n.get("file_path")})

    def find_impacted_apis(self, ctx) -> list[dict]:
        return [
            n
            for n in ctx.impacted_nodes
            if n.get("node_type") == "api_route" or n.get("route_path")
        ]

    def calculate_blast_radius_score(self, dimensions: dict) -> tuple[int, list[dict]]:
        """Weighted 0–100 score with explainable components."""
        dep = min(1.0, dimensions.get("total_nodes", 0) / 50.0)
        wf = min(1.0, dimensions.get("workflows_impacted", 0) / 5.0)
        svc = min(1.0, dimensions.get("services_impacted", 0) / 4.0)
        api = min(1.0, dimensions.get("apis_impacted", 0) / 8.0)
        cp = min(1.0, dimensions.get("critical_paths_count", 0) / 3.0)

        components = [
            {
                "name": "Dependency Reach",
                "points": int(dep * SCORE_WEIGHTS["dependency_reach"]),
                "max_points": SCORE_WEIGHTS["dependency_reach"],
                "evidence": f"{dimensions.get('total_nodes', 0)} nodes in verified blast radius",
            },
            {
                "name": "Workflow Reach",
                "points": int(wf * SCORE_WEIGHTS["workflow_reach"]),
                "max_points": SCORE_WEIGHTS["workflow_reach"],
                "evidence": f"{dimensions.get('workflows_impacted', 0)} workflows touched",
            },
            {
                "name": "Service Reach",
                "points": int(svc * SCORE_WEIGHTS["service_reach"]),
                "max_points": SCORE_WEIGHTS["service_reach"],
                "evidence": f"{dimensions.get('services_impacted', 0)} services affected",
            },
            {
                "name": "API Reach",
                "points": int(api * SCORE_WEIGHTS["api_reach"]),
                "max_points": SCORE_WEIGHTS["api_reach"],
                "evidence": f"{dimensions.get('apis_impacted', 0)} API routes in radius",
            },
            {
                "name": "Critical Path Reach",
                "points": int(cp * SCORE_WEIGHTS["critical_path_reach"]),
                "max_points": SCORE_WEIGHTS["critical_path_reach"],
                "evidence": f"{dimensions.get('critical_paths_count', 0)} critical paths impacted",
            },
        ]
        total = min(100, sum(c["points"] for c in components))
        return total, components

    def identify_critical_paths(self, ctx, paths_hit: list[dict]) -> list[str]:
        return [p["name"] for p in paths_hit]

    def generate_summary(
        self,
        dimensions: dict,
        score: int,
        category: str,
        critical_hit: list[dict],
    ) -> str:
        cp = ", ".join(p["name"] for p in critical_hit[:3]) or "none"
        return (
            f"Blast radius {score}/100 ({category}). "
            f"{dimensions.get('functions_impacted', 0)} functions, "
            f"{dimensions.get('files_impacted', 0)} files, "
            f"{dimensions.get('apis_impacted', 0)} APIs across "
            f"{dimensions.get('workflows_impacted', 0)} workflows and "
            f"{dimensions.get('journeys_impacted', 0)} user journeys. "
            f"Critical paths: {cp}."
        )

    def _apply_report_to_ctx(self, ctx, report: dict) -> None:
        ctx.blast_radius = {
            "functions": report.get("functions_impacted", 0),
            "classes": report.get("classes_impacted", 0),
            "api_routes": report.get("apis_impacted", 0),
            "files": report.get("files_impacted", 0),
            "max_depth": report.get("max_depth", 0),
            "total_nodes": report.get("total_nodes", 0),
            "verified_edges": report.get("verified_edges", 0),
            "scenario": ctx.scenario,
            "workflows_impacted": report.get("workflows_impacted", 0),
            "services_impacted": report.get("services_impacted", 0),
            "journeys_impacted": report.get("journeys_impacted", 0),
            "blast_radius_score": report.get("blast_radius_score", 0),
            "risk_category": report.get("risk_category", "low"),
            "estimated_users_impacted": report.get("estimated_users_impacted", "LOW"),
            "deployment_risk": report.get("deployment_risk", "low"),
            "critical_paths_impacted": [
                p.get("name") for p in report.get("critical_paths_impacted", [])
            ],
            "score_breakdown": report.get("score_breakdown", []),
        }
        ctx.blast_radius_report = report
        ctx.critical_paths_impacted = report.get("critical_paths_impacted", [])
        ctx.journey_impacts = report.get("journey_impacts", [])
        ctx.business_impacts_structured = report.get("business_impacts", [])
        if report.get("business_impacts"):
            ctx.business_impact = self.business_impact.summary_lines(
                report["business_impacts"]
            )
        if report.get("journey_impacts"):
            ctx.user_impact = list(
                dict.fromkeys(j["user_impact"] for j in report["journey_impacts"])
            )[:6]

    def _empty_report(self, ctx) -> dict:
        return {
            "blast_radius_score": 0,
            "risk_category": "safe",
            "functions_impacted": 0,
            "summary": "No source node resolved.",
        }

    async def _read_cache(
        self,
        repo_id: str,
        node_id: str,
        direction: str,
        depth: int,
        db: AsyncSession,
    ) -> dict | None:
        try:
            row = (
                await db.execute(
                    text("""
                        SELECT result FROM blast_radius_cache
                        WHERE repo_id = :repo_id
                          AND target_node_id = :node_id
                          AND direction = :direction
                          AND depth = :depth
                          AND expires_at > NOW()
                        ORDER BY created_at DESC
                        LIMIT 1
                    """),
                    {
                        "repo_id": repo_id,
                        "node_id": node_id,
                        "direction": direction,
                        "depth": depth,
                    },
                )
            ).mappings().first()
            return dict(row["result"]) if row else None
        except Exception as e:
            logger.debug("Blast radius cache read skipped: %s", e)
            return None

    async def _write_cache(
        self,
        repo_id: str,
        node_id: str,
        direction: str,
        depth: int,
        report: dict,
        db: AsyncSession,
    ) -> None:
        import json

        try:
            expires = datetime.now(timezone.utc) + timedelta(hours=CACHE_TTL_HOURS)
            await db.execute(
                text("""
                    DELETE FROM blast_radius_cache
                    WHERE repo_id = :repo_id
                      AND target_node_id = :node_id
                      AND direction = :direction
                      AND depth = :depth
                """),
                {
                    "repo_id": repo_id,
                    "node_id": node_id,
                    "direction": direction,
                    "depth": depth,
                },
            )
            await db.execute(
                text("""
                    INSERT INTO blast_radius_cache (
                        repo_id, target_node_id, direction, depth, result, expires_at
                    ) VALUES (
                        :repo_id, :node_id, :direction, :depth,
                        CAST(:result AS jsonb), :expires_at
                    )
                """),
                {
                    "repo_id": repo_id,
                    "node_id": node_id,
                    "direction": direction,
                    "depth": depth,
                    "result": json.dumps(report, default=str),
                    "expires_at": expires,
                },
            )
        except Exception as e:
            logger.debug("Blast radius cache write skipped: %s", e)
