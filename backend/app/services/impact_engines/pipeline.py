"""Change Intelligence Pipeline — orchestrates six deterministic engines + LLM explainer."""

import logging
import os
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.impact import (
    AffectedAPI,
    DeploymentAdvice,
    ExactDependencies,
    ExactDependencyItem,
    GraphEdge,
    GraphNode,
    ImpactFile,
    ImpactGraph,
    ImpactNode,
    ImpactResult,
    ResolvedEntity,
    RiskScoreBreakdown,
    ConfidenceBreakdown,
    ScoreComponent,
    TestRecommendation,
    WorkflowImpact,
    PrimaryWorkflow,
    WorkflowEvidenceItem,
    ChangeRecommendation,
    BlastRadius,
    BlastRadiusReport,
    BusinessImpactItem,
    CriticalPathSummary,
    JourneyImpactItem,
    RolloutStrategy,
    RollbackStrategy,
)
from app.services.impact_cache import build_cache_key, get_cached_impact, set_cached_impact
from app.services.impact_engines.change_simulator import normalize_scenario
from app.services.impact_engines.context import ImpactContext
from app.services.impact_engines.deployment_engine import DeploymentSafetyEngine
from app.services.impact_engines.blast_radius_engine import BlastRadiusImpactEngine
from app.services.impact_engines.graph_engine import DependencyGraphEngine
from app.services.impact_engines.llm_explainer import LLMExplainerEngine
from app.services.impact_engines.risk_engine import DynamicRiskEngine
from app.services.impact_engines.semantic_resolver import SemanticResolverEngine
from app.services.impact_engines.testing_engine import TestingRecommendationEngine
from app.services.impact_engines.workflow_engine import WorkflowImpactEngine
from app.services.impact_risk_engine import legacy_level_from_score_100

logger = logging.getLogger(__name__)

RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "safe": 4}


class ChangeIntelligencePipeline:
    def __init__(self) -> None:
        self.semantic = SemanticResolverEngine()
        self.graph = DependencyGraphEngine()
        self.blast = BlastRadiusImpactEngine()
        self.workflow = WorkflowImpactEngine()
        self.risk = DynamicRiskEngine()
        self.testing = TestingRecommendationEngine()
        self.deployment = DeploymentSafetyEngine()
        self.llm = LLMExplainerEngine()

    async def analyze(
        self,
        query: str,
        repo_id: str,
        max_depth: int,
        direction: str,
        db: AsyncSession,
        *,
        natural_language: bool = True,
        repo_name: str = "",
        scenario: str = "modify",
    ) -> ImpactResult:
        cache_key = build_cache_key(
            repo_id,
            f"{query}|nl={natural_language}|sc={scenario}",
            max_depth,
            direction,
        )
        cached = await get_cached_impact(cache_key)
        if cached is not None:
            return cached

        start = time.time()
        ctx = ImpactContext(
            query=query.strip(),
            repo_id=repo_id,
            repo_name=repo_name or "repository",
            max_depth=max_depth,
            direction=direction,
            scenario=normalize_scenario(scenario),
            natural_language=natural_language,
        )

        await self.semantic.run(ctx, db)
        if not ctx.source_node:
            return self._empty(query, int((time.time() - start) * 1000))

        await self.graph.traverse(ctx, db)
        await self.graph.enrich_metadata(ctx, db)
        self.graph.attach_evidence(ctx)
        await self.graph.load_subgraph_edges(ctx, db)
        self.graph.compute_centrality(ctx)
        await self.blast.run(ctx, db)
        self._apply_blast_tiers_to_nodes(ctx)
        self.graph.extract_exact_dependencies(ctx)

        await self.workflow.run(ctx, db)
        self.risk.run(ctx)
        self.testing.run(ctx)
        self.deployment.run(ctx)
        await self.llm.run(ctx)

        ctx.files_grouped = self._group_files(ctx.impacted_nodes)
        ctx.analysis_time_ms = int((time.time() - start) * 1000)

        result = self._to_result(ctx)
        await set_cached_impact(cache_key, result)
        return result

    def _group_files(self, nodes: list[dict]) -> list[dict]:
        by_path: dict[str, list[dict]] = {}
        for n in nodes:
            path = n.get("file_path") or "unknown"
            by_path.setdefault(path, []).append(n)
        files = []
        for path, path_nodes in by_path.items():
            max_s = max(n["risk_score"] for n in path_nodes)
            tier = legacy_level_from_score_100(int(max_s * 100))
            if tier == "safe":
                tier = "low"
            files.append(
                {
                    "file_path": path,
                    "file_name": os.path.basename(path) if path else "unknown",
                    "affected_functions": [n["name"] for n in path_nodes],
                    "risk_level": tier,
                }
            )
        files.sort(key=lambda f: RISK_ORDER.get(f["risk_level"], 99))
        return files

    def _empty(self, query: str, ms: int) -> ImpactResult:
        return ImpactResult(
            query=query,
            resolved_query="",
            resolution_confidence=0,
            matched_entities=[],
            source_node=None,
            impacted_nodes=[],
            impacted_files=[],
            graph=ImpactGraph(nodes=[], edges=[]),
            risk_level="low",
            risk_score=0,
            risk_score_100=0,
            confidence=0,
            executive_summary="No matching component in analyzed graph.",
            why_this_matters="",
            blast_radius=BlastRadius(),
            business_impact=[],
            engineering_impact=[],
            developer_impact=[],
            workflow_impact=[],
            primary_workflow=None,
            affected_journeys=[],
            workflow_evidence=[],
            workflow_confidence=0.0,
            blast_radius_report=None,
            journey_impact_items=[],
            business_impact_items=[],
            user_impact=[],
            affected_systems=[],
            affected_apis=[],
            explanation="No match found",
            risk_analysis="",
            ai_recommendation="",
            staff_engineer_recommendation="",
            recommended_tests=[],
            deployment_advice=None,
            rollout_strategy=RolloutStrategy(strategy="n/a", steps=[]),
            rollback_strategy=RollbackStrategy(strategy="n/a", steps=[]),
            monitoring_plan=[],
            risk_score_breakdown=RiskScoreBreakdown(total=0, tier="safe", components=[]),
            confidence_breakdown=ConfidenceBreakdown(total=0, components=[]),
            change_recommendation=ChangeRecommendation(
                decision="requires_review",
                should_proceed=False,
                label="Cannot analyze — source not found",
            ),
            pr_checklist=[],
            qa_checklist=[],
            rollback_plan=[],
            total_affected_functions=0,
            total_affected_files=0,
            analysis_time_ms=ms,
            scenario="modify",
            version="5.0",
        )

    def _apply_blast_tiers_to_nodes(self, ctx: ImpactContext) -> None:
        """Color graph nodes from blast depth + score (deterministic)."""
        br_score = ctx.blast_radius.get("blast_radius_score", 0)
        category = ctx.blast_radius.get("risk_category", "low")

        def tier_for_node(n: dict) -> str:
            depth = n.get("depth", 0)
            if depth >= 4 or br_score >= 81:
                return "critical"
            if depth >= 3 or br_score >= 61:
                return "high"
            if depth >= 2 or br_score >= 41:
                return "medium"
            if br_score >= 21:
                return "low"
            return "safe" if category == "safe" else "low"

        for n in ctx.impacted_nodes:
            n["risk_tier"] = tier_for_node(n)

    def _build_blast_radius_report(self, ctx: ImpactContext) -> BlastRadiusReport | None:
        r = ctx.blast_radius_report
        if not r:
            return None
        cp = [
            CriticalPathSummary(
                id=p.get("id", ""),
                name=p.get("name", ""),
                criticality=p.get("criticality", "high"),
                description=p.get("description"),
                impacted_node_names=p.get("impacted_node_names", []),
            )
            for p in r.get("critical_paths_impacted", [])
        ]
        breakdown = [
            ScoreComponent(
                name=c.get("name", ""),
                points=c.get("points", 0),
                max_points=c.get("max_points", 0),
                evidence=c.get("evidence", ""),
            )
            for c in r.get("score_breakdown", [])
        ]
        return BlastRadiusReport(
            blast_radius_score=r.get("blast_radius_score", 0),
            risk_category=r.get("risk_category", "safe"),
            functions_impacted=r.get("functions_impacted", 0),
            classes_impacted=r.get("classes_impacted", 0),
            files_impacted=r.get("files_impacted", 0),
            apis_impacted=r.get("apis_impacted", 0),
            workflows_impacted=r.get("workflows_impacted", 0),
            services_impacted=r.get("services_impacted", 0),
            journeys_impacted=r.get("journeys_impacted", 0),
            estimated_users_impacted=r.get("estimated_users_impacted", "LOW"),
            deployment_risk=r.get("deployment_risk", "low"),
            critical_paths_impacted=cp,
            service_names=r.get("service_names", []),
            journey_names=r.get("journey_names", []),
            workflow_names=r.get("workflow_names", []),
            score_breakdown=breakdown,
            summary=r.get("summary", ""),
            journey_impacts=[
                JourneyImpactItem(**j) for j in r.get("journey_impacts", [])
            ],
            business_impacts=[
                BusinessImpactItem(**b) for b in r.get("business_impacts", [])
            ],
        )

    def _to_result(self, ctx: ImpactContext) -> ImpactResult:
        rb = ctx.risk_breakdown
        components = rb.get("components", {})
        risk_components = [
            ScoreComponent(
                name=k.replace("_", " ").title(),
                points=v["points"],
                max_points=v["max"],
                evidence=v["evidence"],
            )
            for k, v in components.items()
        ]
        cb = ctx.confidence_breakdown.get("components", {})
        conf_components = [
            ScoreComponent(
                name=k.replace("_", " ").title(),
                points=int(v * 100),
                max_points=100,
                evidence=f"weight {v}",
            )
            for k, v in cb.items()
        ]

        graph_nodes = []
        source_tier = ctx.blast_radius.get("risk_category", "medium")
        if source_tier == "safe":
            source_tier = "low"
        if ctx.source_node:
            graph_nodes.append(
                GraphNode(
                    id=ctx.source_node["id"],
                    name=ctx.source_node["name"],
                    node_type=ctx.source_node.get("node_type", "?"),
                    file_path=ctx.source_node.get("file_path", ""),
                    risk_tier=source_tier,
                    is_source=True,
                    depth=0,
                )
            )
        for n in ctx.impacted_nodes[:80]:
            graph_nodes.append(
                GraphNode(
                    id=n["id"],
                    name=n["name"],
                    node_type=n.get("node_type", "?"),
                    file_path=n.get("file_path", ""),
                    risk_tier=n.get("risk_tier", "low"),
                    is_source=False,
                    depth=n.get("depth", 1),
                )
            )

        legacy = legacy_level_from_score_100(ctx.risk_score_100)

        return ImpactResult(
            query=ctx.query,
            resolved_query=ctx.source_node["name"] if ctx.source_node else ctx.query,
            resolution_confidence=ctx.resolution_confidence,
            matched_entities=[ResolvedEntity(**e) for e in ctx.matched_entities],
            source_node=ctx.source_node,
            impacted_nodes=[
                ImpactNode(
                    id=n["id"],
                    name=n["name"],
                    node_type=n["node_type"],
                    file_path=n.get("file_path") or "",
                    start_line=n.get("start_line"),
                    end_line=n.get("end_line"),
                    depth=n["depth"],
                    direction=n.get("direction", "downstream"),
                    risk_score=n["risk_score"],
                    edge_type=n.get("edge_type") or "",
                    inclusion_reason=n.get("inclusion_reason"),
                    risk_tier=n.get("risk_tier"),
                    http_method=n.get("http_method"),
                    route_path=n.get("route_path"),
                )
                for n in ctx.impacted_nodes
            ],
            impacted_files=[ImpactFile(**f) for f in ctx.files_grouped],
            graph=ImpactGraph(
                nodes=graph_nodes,
                edges=[GraphEdge(**e) for e in ctx.graph_edges],
            ),
            exact_dependencies=self._build_exact_dependencies(ctx),
            risk_level=legacy,
            risk_score=ctx.risk_score_100 / 100.0,
            risk_score_100=ctx.risk_score_100,
            confidence=ctx.confidence,
            executive_summary=ctx.executive_summary,
            why_this_matters=ctx.why_this_matters,
            blast_radius=BlastRadius(
                **{
                    k: v
                    for k, v in ctx.blast_radius.items()
                    if k in BlastRadius.model_fields
                }
            ),
            blast_radius_report=self._build_blast_radius_report(ctx),
            journey_impact_items=[
                JourneyImpactItem(**j) for j in ctx.journey_impacts
            ],
            business_impact_items=[
                BusinessImpactItem(**b) for b in ctx.business_impacts_structured
            ],
            business_impact=ctx.business_impact,
            engineering_impact=ctx.engineering_impact,
            developer_impact=ctx.engineering_impact,
            workflow_impact=[WorkflowImpact(**w) for w in ctx.workflow_impact],
            primary_workflow=(
                PrimaryWorkflow(**ctx.primary_workflow)
                if ctx.primary_workflow
                else None
            ),
            affected_journeys=ctx.affected_journeys,
            workflow_evidence=[
                WorkflowEvidenceItem(**e) for e in ctx.workflow_evidence
            ],
            workflow_confidence=ctx.workflow_confidence,
            user_impact=ctx.user_impact,
            affected_systems=ctx.affected_services or ctx.services,
            affected_apis=[AffectedAPI(**a) for a in ctx.apis],
            explanation=ctx.executive_summary,
            risk_analysis=self._risk_analysis_text(ctx),
            ai_recommendation=ctx.staff_engineer_recommendation,
            staff_engineer_recommendation=ctx.staff_engineer_recommendation,
            recommended_tests=[
                TestRecommendation(
                    title=t["title"],
                    priority=t["priority"],
                    reason=t["reason"],
                    evidence=t.get("evidence"),
                )
                for t in ctx.recommended_tests
            ],
            deployment_advice=DeploymentAdvice(
                summary=ctx.rollout_strategy.get("strategy", ""),
                recommendations=ctx.rollout_strategy.get("steps", []),
                monitoring=ctx.monitoring_plan,
                rollback_trigger=ctx.rollback_strategy.get("trigger"),
            ),
            rollout_strategy=RolloutStrategy(
                strategy=ctx.rollout_strategy.get("strategy", ""),
                steps=ctx.rollout_strategy.get("steps", []),
                feature_flag_recommended=ctx.rollout_strategy.get(
                    "feature_flag_recommended", False
                ),
                canary_recommended=ctx.rollout_strategy.get("canary_recommended", False),
            ),
            rollback_strategy=RollbackStrategy(
                strategy=ctx.rollback_strategy.get("strategy", ""),
                steps=ctx.rollback_strategy.get("steps", []),
                trigger=ctx.rollback_strategy.get("trigger"),
            ),
            monitoring_plan=ctx.monitoring_plan,
            risk_score_breakdown=RiskScoreBreakdown(
                total=rb.get("total", 0),
                tier=rb.get("tier", "low"),
                components=risk_components,
            ),
            confidence_breakdown=ConfidenceBreakdown(
                total=ctx.confidence,
                components=conf_components,
            ),
            change_recommendation=ChangeRecommendation(
                decision=ctx.change_recommendation,
                should_proceed=ctx.should_proceed,
                label=ctx.proceed_label,
            ),
            pr_checklist=[],
            qa_checklist=[],
            rollback_plan=ctx.rollback_strategy.get("steps", []),
            total_affected_functions=len(ctx.impacted_nodes),
            total_affected_files=len(ctx.files_grouped),
            analysis_time_ms=ctx.analysis_time_ms,
            warning=ctx.traversal_warning,
            scenario=ctx.scenario,
            version="5.0",
        )

    def _risk_analysis_text(self, ctx: ImpactContext) -> str:
        parts = [
            f"Risk {ctx.risk_score_100}/100 ({ctx.risk_breakdown.get('tier', 'low')})."
        ]
        for c in ctx.risk_breakdown.get("components", {}).values():
            if c["points"] > 0:
                parts.append(f"{c['points']}pts: {c['evidence']}")
        return " ".join(parts[:6])

    def _build_exact_dependencies(self, ctx: ImpactContext) -> ExactDependencies | None:
        raw = ctx.exact_dependencies
        if not raw:
            return None

        def _items(key: str) -> list[ExactDependencyItem]:
            return [ExactDependencyItem(**i) for i in raw.get(key, [])]

        return ExactDependencies(
            level_1_direct=_items("level_1_direct"),
            level_1_incoming=_items("level_1_incoming"),
            level_2_indirect=_items("level_2_indirect"),
            level_3_workflow=_items("level_3_workflow"),
            database_dependencies=_items("database_dependencies"),
            api_dependencies=_items("api_dependencies"),
            file_dependencies=raw.get("file_dependencies", []),
        )
