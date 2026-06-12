"""Explainable deterministic risk scoring engine."""

import re
from typing import Any

from app.services.impact_risk_engine import risk_tier_from_score

AUTH_PATTERN = re.compile(r"auth|oauth|login|session|token|jwt|github", re.I)
PUBLIC_API_PATTERN = re.compile(r"\b(get|post|delete|put|patch)\b|/api/|/auth/|/login|/oauth", re.I)
HISTORICAL_TAGS = frozenset({"incident", "outage", "hotfix", "production-bug"})


class ExplainableRiskEngine:
    def run(self, ctx: Any) -> None:
        ctx.apis = self.extract_apis(ctx)
        ctx.services = self.extract_services(ctx)
        ctx.affected_services = ctx.services

        factors = {
            "Dependency Reach": self.calculate_dependency_risk(ctx),
            "Workflow Reach": self.calculate_workflow_risk(ctx),
            "Service Reach": self.calculate_service_risk(ctx),
            "API Reach": self.calculate_api_risk(ctx),
            "Journey Reach": self.calculate_journey_risk(ctx),
            "Business Reach": self.calculate_business_risk(ctx),
            "Centrality Reach": self.calculate_centrality_risk(ctx),
            "Critical Path Reach": self.calculate_critical_path_risk(ctx),
            "Historical Risk": self.calculate_historical_risk(ctx),
        }

        total = min(100, sum(f["score"] for f in factors.values()))
        tier = risk_tier_from_score(total)
        breakdown = self.generate_risk_breakdown(factors, total)

        ctx.risk_breakdown = breakdown
        ctx.risk_score_100 = total
        ctx.risk_level = tier
        ctx.confidence_breakdown = self.calculate_confidence(ctx)
        ctx.confidence = ctx.confidence_breakdown["total"]
        ctx.change_recommendation, ctx.should_proceed, ctx.proceed_label = (
            self._change_decision(total, ctx.scenario, len(ctx.apis))
        )

    def calculate_dependency_risk(self, ctx: Any) -> dict[str, Any]:
        affected_nodes = int(ctx.blast_radius.get("total_nodes", 0))
        depth = int(ctx.blast_radius.get("max_depth", 0))
        score = min(20, int(affected_nodes * 2 + depth * 1))
        return {
            "score": score,
            "weight": 20,
            "evidence": {
                "affected_nodes": affected_nodes,
                "dependency_depth": depth,
                "example_nodes": [n.get("name") for n in ctx.impacted_nodes[:5]],
            },
        }

    def calculate_workflow_risk(self, ctx: Any) -> dict[str, Any]:
        workflow_count = max(
            int(ctx.blast_radius.get("workflows_impacted", 0)),
            len(ctx.workflow_impact or []),
        )
        critical_bonus = sum(
            2
            for item in ctx.workflow_impact
            if item.get("criticality", "medium").lower() == "high"
        )
        score = min(15, workflow_count * 5 + critical_bonus)
        return {
            "score": score,
            "weight": 15,
            "evidence": {
                "workflow_count": workflow_count,
                "critical_workflows": [
                    item.get("workflow_name")
                    for item in ctx.workflow_impact
                    if item.get("criticality", "medium").lower() == "high"
                ][:5],
            },
        }

    def calculate_service_risk(self, ctx: Any) -> dict[str, Any]:
        service_count = max(len(ctx.affected_services or []), len(ctx.services or []))
        score = min(15, int(service_count * 5))
        return {
            "score": score,
            "weight": 15,
            "evidence": {
                "service_count": service_count,
                "services": ctx.affected_services or ctx.services or [],
            },
        }

    def calculate_api_risk(self, ctx: Any) -> dict[str, Any]:
        routes = ctx.apis or []
        public_count = sum(
            1 for api in routes if PUBLIC_API_PATTERN.search(api.get("path", "") or api.get("name", ""))
        )
        internal_count = max(0, len(routes) - public_count)
        score = min(10, int(public_count * 2 + internal_count * 1))
        return {
            "score": score,
            "weight": 10,
            "evidence": {
                "public_api_count": public_count,
                "internal_api_count": internal_count,
                "examples": [f"{a.get('method')} {a.get('path')}" for a in routes[:6]],
            },
        }

    def calculate_journey_risk(self, ctx: Any) -> dict[str, Any]:
        journey_count = max(len(ctx.affected_journeys or []), int(ctx.blast_radius.get("journeys_impacted", 0)))
        severity_bonus = sum(
            2 for item in getattr(ctx, "journey_impacts", []) if item.get("severity", "medium").lower() == "high"
        )
        score = min(10, journey_count * 4 + severity_bonus)
        return {
            "score": score,
            "weight": 10,
            "evidence": {
                "journey_count": journey_count,
                "journeys": ctx.affected_journeys or [],
            },
        }

    def calculate_business_risk(self, ctx: Any) -> dict[str, Any]:
        impacts = getattr(ctx, "business_impacts_structured", []) or []
        if not impacts and getattr(ctx, "business_impact", None):
            impacts = [
                {"category": b.split()[0] if isinstance(b, str) else "unknown", "severity": "medium"}
                for b in ctx.business_impact
            ]
        categories = {item.get("category") for item in impacts if item.get("category")}
        severity_points = sum(
            2 if item.get("severity", "medium").lower() == "high" else 1
            for item in impacts
        )
        score = min(10, len(categories) * 3 + severity_points)
        return {
            "score": score,
            "weight": 10,
            "evidence": {
                "business_categories": sorted(categories),
                "business_impacts": impacts[:5],
            },
        }

    def calculate_centrality_risk(self, ctx: Any) -> dict[str, Any]:
        centrality = list(ctx.centrality.values() or [])
        avg = float(sum(centrality) / len(centrality)) if centrality else 0.0
        score = min(10, int(avg * 10))
        top_nodes = sorted(
            ctx.impacted_nodes,
            key=lambda n: ctx.centrality.get(n["id"], 0),
            reverse=True,
        )[:4]
        return {
            "score": score,
            "weight": 10,
            "evidence": {
                "average_centrality": round(avg, 3),
                "top_nodes": [n.get("name") for n in top_nodes],
            },
        }

    def calculate_critical_path_risk(self, ctx: Any) -> dict[str, Any]:
        critical_paths = ctx.blast_radius.get("critical_paths_impacted", []) or []
        path_count = len(critical_paths)
        score = min(10, int(path_count * 5))
        return {
            "score": score,
            "weight": 10,
            "evidence": {
                "critical_path_count": path_count,
                "critical_paths": critical_paths[:4],
            },
        }

    def calculate_historical_risk(self, ctx: Any) -> dict[str, Any]:
        incident_nodes = [
            n
            for n in ctx.impacted_nodes
            if any(tag.lower() in HISTORICAL_TAGS for tag in (n.get("tags") or []))
        ]
        score = 8 if incident_nodes else 0
        return {
            "score": score,
            "weight": 10,
            "evidence": {
                "incident_nodes": [n.get("name") for n in incident_nodes[:5]],
                "historical_matches": [tag for n in incident_nodes for tag in (n.get("tags") or []) if tag.lower() in HISTORICAL_TAGS],
            },
        }

    def calculate_confidence(self, ctx: Any) -> dict[str, Any]:
        graph_nodes = max(1, int(ctx.blast_radius.get("total_nodes", 0)))
        graph_edges = max(1, len(ctx.graph_edges or []))
        graph_coverage = min(1.0, graph_edges / (graph_nodes * 2.5))
        workflow_coverage = min(1.0, int(ctx.blast_radius.get("workflows_impacted", 0)) / 5.0)
        api_coverage = min(1.0, len(ctx.apis or []) / 8.0)
        journey_coverage = min(1.0, len(ctx.affected_journeys or []) / 4.0)
        evidence_completeness = 1.0 if ctx.impacted_nodes else 0.2
        total = round(
            min(
                0.98,
                graph_coverage * 0.25
                + workflow_coverage * 0.22
                + api_coverage * 0.22
                + journey_coverage * 0.18
                + evidence_completeness * 0.13,
            ),
            2,
        )
        return {
            "total": total,
            "components": {
                "graph_coverage": {
                    "points": int(graph_coverage * 100),
                    "max": 100,
                    "evidence": f"{graph_edges} verified graph edges over {graph_nodes} nodes",
                },
                "workflow_coverage": {
                    "points": int(workflow_coverage * 100),
                    "max": 100,
                    "evidence": f"{ctx.blast_radius.get('workflows_impacted', 0)} workflows impacted",
                },
                "api_coverage": {
                    "points": int(api_coverage * 100),
                    "max": 100,
                    "evidence": f"{len(ctx.apis or [])} APIs discovered",
                },
                "journey_coverage": {
                    "points": int(journey_coverage * 100),
                    "max": 100,
                    "evidence": f"{len(ctx.affected_journeys or [])} journeys identified",
                },
                "evidence_completeness": {
                    "points": int(evidence_completeness * 100),
                    "max": 100,
                    "evidence": "verified impacted nodes present" if ctx.impacted_nodes else "no impact evidence",
                },
            },
        }

    def generate_risk_breakdown(self, factors: dict[str, dict[str, Any]], total: int) -> dict[str, Any]:
        return {
            "total": total,
            "tier": risk_tier_from_score(total),
            "components": {
                name: {
                    "points": value["score"],
                    "max": value["weight"],
                    "evidence": value["evidence"],
                }
                for name, value in factors.items()
            },
        }

    def compute_profile_from_metrics(
        self,
        metrics: dict[str, Any],
        entity_type: str,
        entity_id: str,
        repo_id: str,
    ) -> dict[str, Any]:
        dependency_nodes = int(metrics.get("dependency_count", 0))
        depth_estimate = min(10, max(1, int(dependency_nodes / 2)))
        workflow_count = int(metrics.get("workflow_count", 0))
        service_count = int(metrics.get("service_count", 0))
        api_count = int(metrics.get("api_count", 0))
        journey_count = int(metrics.get("journey_count", 0))
        centrality_score = float(metrics.get("centrality_score", 0.0) or 0.0)
        critical_path_count = int(metrics.get("critical_path_count", 0))

        factors = [
            {
                "factor_name": "Dependency Reach",
                "factor_score": min(20, int(dependency_nodes * 2 + depth_estimate * 1)),
                "weight": 20,
                "evidence": {
                    "dependency_count": dependency_nodes,
                    "dependency_depth": depth_estimate,
                },
            },
            {
                "factor_name": "Workflow Reach",
                "factor_score": min(15, workflow_count * 5),
                "weight": 15,
                "evidence": {"workflow_count": workflow_count},
            },
            {
                "factor_name": "Service Reach",
                "factor_score": min(15, service_count * 5),
                "weight": 15,
                "evidence": {"service_count": service_count},
            },
            {
                "factor_name": "API Reach",
                "factor_score": min(10, api_count * 3),
                "weight": 10,
                "evidence": {"api_count": api_count},
            },
            {
                "factor_name": "Journey Reach",
                "factor_score": min(10, journey_count * 4),
                "weight": 10,
                "evidence": {"journey_count": journey_count},
            },
            {
                "factor_name": "Business Reach",
                "factor_score": min(10, min(10, journey_count * 2 + service_count)),
                "weight": 10,
                "evidence": {
                    "journey_count": journey_count,
                    "service_count": service_count,
                },
            },
            {
                "factor_name": "Centrality Reach",
                "factor_score": min(10, int(centrality_score * 10)),
                "weight": 10,
                "evidence": {"centrality_score": round(centrality_score, 3)},
            },
            {
                "factor_name": "Critical Path Reach",
                "factor_score": min(10, critical_path_count * 5),
                "weight": 10,
                "evidence": {"critical_path_count": critical_path_count},
            },
            {
                "factor_name": "Historical Risk",
                "factor_score": 0,
                "weight": 10,
                "evidence": {"historical_matches": []},
            },
        ]
        total = min(100, sum(item["factor_score"] for item in factors))
        return {
            "repo_id": repo_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "risk_score": float(total),
            "risk_category": risk_tier_from_score(int(total)),
            "confidence": 0.75,
            "risk_factors": factors,
            "change_reason": "Recomputed from precomputed impact metrics.",
            "changed": False,
        }

    def compute_repo_profile_from_repo_metrics(
        self,
        repo_id: str,
        metric_rows: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not metric_rows:
            return None
        totals = self._aggregate_metrics(metric_rows)
        rows = totals.pop("rows")
        avg_centrality = totals["centrality_score"] / rows if rows else 0.0
        factors = [
            {
                "factor_name": "Dependency Reach",
                "factor_score": min(20, int(totals["dependency_count"] * 1.2)),
                "weight": 20,
                "evidence": {"total_dependency_count": totals["dependency_count"]},
            },
            {
                "factor_name": "Workflow Reach",
                "factor_score": min(15, int(totals["workflow_count"] * 4)),
                "weight": 15,
                "evidence": {"total_workflows": totals["workflow_count"]},
            },
            {
                "factor_name": "Service Reach",
                "factor_score": min(15, int(totals["service_count"] * 4)),
                "weight": 15,
                "evidence": {"total_services": totals["service_count"]},
            },
            {
                "factor_name": "API Reach",
                "factor_score": min(10, int(totals["api_count"] * 2)),
                "weight": 10,
                "evidence": {"total_apis": totals["api_count"]},
            },
            {
                "factor_name": "Journey Reach",
                "factor_score": min(10, int(totals["journey_count"] * 3)),
                "weight": 10,
                "evidence": {"total_journeys": totals["journey_count"]},
            },
            {
                "factor_name": "Business Reach",
                "factor_score": min(10, int(totals["journey_count"] * 2 + totals["service_count"])),
                "weight": 10,
                "evidence": {
                    "totals": {
                        "journey_count": totals["journey_count"],
                        "service_count": totals["service_count"],
                    }
                },
            },
            {
                "factor_name": "Centrality Reach",
                "factor_score": min(10, int(avg_centrality * 10)),
                "weight": 10,
                "evidence": {"average_centrality": round(avg_centrality, 3)},
            },
            {
                "factor_name": "Critical Path Reach",
                "factor_score": min(10, int(totals["critical_path_count"] * 4)),
                "weight": 10,
                "evidence": {"total_critical_paths": totals["critical_path_count"]},
            },
            {
                "factor_name": "Historical Risk",
                "factor_score": 0,
                "weight": 10,
                "evidence": {"historical_matches": []},
            },
        ]
        total = min(100, sum(item["factor_score"] for item in factors))
        return {
            "repo_id": repo_id,
            "entity_type": "repo",
            "entity_id": repo_id,
            "risk_score": float(total),
            "risk_category": risk_tier_from_score(int(total)),
            "confidence": 0.80,
            "risk_factors": factors,
            "change_reason": "Recomputed overall repository risk profile.",
            "changed": False,
        }

    def extract_apis(self, ctx: Any) -> list[dict[str, Any]]:
        apis = []
        for n in ctx.impacted_nodes:
            if n.get("node_type") not in ("api_route",) and not n.get("route_path"):
                continue
            apis.append(
                {
                    "method": (n.get("http_method") or "GET").upper(),
                    "path": n.get("route_path") or n.get("name") or "unknown",
                    "node_id": str(n.get("id")),
                    "name": n.get("name", ""),
                    "file_path": n.get("file_path", ""),
                    "inclusion_reason": f"API reachable in blast radius at depth {n.get('depth', 0)}",
                }
            )
        return apis

    def extract_services(self, ctx: Any) -> list[str]:
        services = set()
        for wf in ctx.workflow_impact or []:
            service = wf.get("service_name")
            if service:
                services.add(service)
        return sorted(services)

    def _change_decision(self, score: int, scenario: str, api_count: int) -> tuple[str, bool, str]:
        if scenario == "delete" and (score >= 50 or api_count >= 1):
            return "block", False, "Do not delete — dependents exist on verified graph evidence"
        if score >= 81:
            return "block", False, "Critical risk — escalate to architecture before merging"
        if score >= 61:
            return "requires_review", False, "High risk — full regression and staged rollout required"
        if score >= 41:
            return "proceed_with_caution", True, "Medium risk — targeted tests then deploy with monitoring"
        if score >= 21:
            return "proceed_with_caution", True, "Low risk — standard PR review sufficient"
        return "proceed", True, "Safe to proceed — minimal verified change surface"
