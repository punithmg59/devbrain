"""Engine 3: Dynamic Risk Engine — scored breakdown from graph evidence (no LLM)."""

import re

from app.services.impact_risk_engine import ImpactRiskEngine, legacy_level_from_score_100, risk_tier_from_score

AUTH = re.compile(r"auth|oauth|login|session|token|jwt|github", re.I)
DB = re.compile(r"database|db_|postgres|sqlalchemy|redis|migrate", re.I)
CRITICAL = re.compile(r"main\.py|router|middleware|connect|analyze|oauth", re.I)

# Placeholder for future incident store — deterministic weight when tags match
INCIDENT_TAGS = frozenset({"incident", "outage", "hotfix", "production-bug"})


class DynamicRiskEngine:
    def __init__(self) -> None:
        self._base = ImpactRiskEngine()

    def run(self, ctx) -> None:
        max_depth = ctx.max_depth
        for n in ctx.impacted_nodes:
            self._base.score_node(n, max_depth)
            cid = ctx.centrality.get(n["id"], 0)
            if cid > 0.6:
                n["risk_score"] = min(1.0, n["risk_score"] + 0.1)
                n["risk_tier"] = risk_tier_from_score(int(n["risk_score"] * 100))

        apis = self._base.extract_apis(ctx.impacted_nodes)
        ctx.apis = apis
        ctx.services = self._base.infer_systems(ctx.impacted_nodes, ctx.source_node)

        breakdown = self._compute_breakdown(ctx)
        ctx.risk_breakdown = breakdown
        ctx.risk_score_100 = breakdown["total"]
        ctx.risk_level = legacy_level_from_score_100(ctx.risk_score_100)

        ctx.confidence_breakdown = self._confidence_breakdown(ctx)
        ctx.confidence = ctx.confidence_breakdown["total"]

        ctx.change_recommendation, ctx.should_proceed, ctx.proceed_label = (
            self._change_decision(ctx.risk_score_100, ctx.scenario, len(apis))
        )

    def _compute_breakdown(self, ctx) -> dict:
        nodes = ctx.impacted_nodes
        br = ctx.blast_radius
        text = self._blob(ctx)

        depth_pts = min(15, br.get("max_depth", 0) * 3)
        api_pts = min(25, br.get("api_routes", 0) * 8)
        fn_pts = min(15, br.get("functions", 0) * 2)
        file_pts = min(10, br.get("files", 0) * 2)
        auth_pts = 20 if AUTH.search(text) else 0
        db_pts = 12 if DB.search(text) else 0
        critical_pts = 15 if CRITICAL.search(text) else 0

        centrality_pts = 0
        if ctx.centrality:
            avg_c = sum(ctx.centrality.values()) / len(ctx.centrality)
            centrality_pts = min(13, int(avg_c * 15))

        incident_pts = 0
        for n in nodes:
            tags = n.get("tags") or []
            if INCIDENT_TAGS.intersection({t.lower() for t in tags}):
                incident_pts = 8
                break

        workflow_pts = min(12, len(ctx.workflow_impact) * 4) if ctx.workflow_impact else 0

        if ctx.scenario == "delete" and br.get("total_nodes", 0) > 3:
            workflow_pts += 10

        total = min(
            100,
            depth_pts
            + api_pts
            + fn_pts
            + file_pts
            + auth_pts
            + db_pts
            + critical_pts
            + centrality_pts
            + incident_pts
            + workflow_pts,
        )

        return {
            "total": total,
            "tier": risk_tier_from_score(total),
            "components": {
                "dependency_depth": {"points": depth_pts, "max": 15, "evidence": f"max depth {br.get('max_depth')}"},
                "api_criticality": {"points": api_pts, "max": 25, "evidence": f"{br.get('api_routes')} API routes in blast radius"},
                "function_spread": {"points": fn_pts, "max": 15, "evidence": f"{br.get('functions')} functions"},
                "file_spread": {"points": file_pts, "max": 10, "evidence": f"{br.get('files')} files"},
                "authentication": {"points": auth_pts, "max": 20, "evidence": "auth/oauth/session in graph" if auth_pts else "none"},
                "database": {"points": db_pts, "max": 12, "evidence": "data layer in graph" if db_pts else "none"},
                "critical_modules": {"points": critical_pts, "max": 15, "evidence": "core paths touched" if critical_pts else "none"},
                "centrality": {"points": centrality_pts, "max": 13, "evidence": "hub nodes in subgraph"},
                "historical_incidents": {"points": incident_pts, "max": 8, "evidence": "node tags" if incident_pts else "none"},
                "workflow_criticality": {"points": workflow_pts, "max": 22, "evidence": f"scenario={ctx.scenario}"},
            },
        }

    def _confidence_breakdown(self, ctx) -> dict:
        resolution = min(0.35, ctx.resolution_confidence * 0.35)
        graph = min(0.35, len(ctx.impacted_nodes) * 0.02 + len(ctx.graph_edges) * 0.01)
        evidence = 0.2 if ctx.graph_edges else 0.1
        complete = 0.1 if not ctx.traversal_warning else 0.0
        total = round(min(0.98, resolution + graph + evidence + complete), 2)
        return {
            "total": total,
            "components": {
                "resolution_match": round(resolution, 2),
                "graph_coverage": round(graph, 2),
                "edge_verification": round(evidence, 2),
                "query_completeness": round(complete, 2),
            },
        }

    def _change_decision(self, score: int, scenario: str, api_count: int) -> tuple[str, bool, str]:
        if scenario == "delete" and (score >= 50 or api_count >= 1):
            return "block", False, "Do not delete — dependents exist on verified graph edges"
        if score >= 81:
            return "block", False, "Critical risk — escalate to architect before merging"
        if score >= 61:
            return "requires_review", False, "High risk — full regression and staged rollout required"
        if score >= 41:
            return "proceed_with_caution", True, "Medium risk — targeted tests then deploy with monitoring"
        if score >= 21:
            return "proceed_with_caution", True, "Low risk — standard PR review sufficient"
        return "proceed", True, "Safe to proceed — minimal verified blast radius"

    def _blob(self, ctx) -> str:
        parts = []
        if ctx.source_node:
            parts.append(ctx.source_node.get("name", ""))
        for n in ctx.impacted_nodes[:40]:
            parts.append(f"{n.get('name')} {n.get('file_path')}")
        return " ".join(parts)
