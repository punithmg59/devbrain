"""Deterministic change simulation engine for DevBrain."""

from __future__ import annotations

import json
import logging
from uuid import UUID
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    EvidenceChain,
    SimulationHistory,
    SimulationImpact,
    SimulationProfile,
)
from app.services.critical_path_service import CriticalPathService
from app.services.deployment_safety_service import DeploymentSafetyService
from app.services.failure_classifier import FailureClassifier
from app.services.failure_probability_service import FailureProbabilityService
from app.services.impact_service import ImpactService
from app.services.journey_failure_service import JourneyFailureService
from app.services.recovery_complexity_service import RecoveryComplexityService
from app.services.service_failure_service import ServiceFailureService
from app.services.impact_engines.change_simulator import normalize_scenario
from app.services.journey_service import journey_names_for_workflows

logger = logging.getLogger(__name__)


class ChangeSimulator:
    def __init__(self) -> None:
        self.impact_service = ImpactService()
        self.failure_probability = FailureProbabilityService()
        self.classifier = FailureClassifier()
        self.service_failure = ServiceFailureService()
        self.journey_failure = JourneyFailureService()
        self.recovery_complexity = RecoveryComplexityService()
        self.deployment_safety = DeploymentSafetyService()
        self.critical_path = CriticalPathService()

    async def simulate(
        self,
        query: str,
        repo_id: str,
        scenario: str,
        db: AsyncSession,
        *,
        max_depth: int = 6,
        direction: str = "both",
        natural_language: bool = True,
    ) -> dict[str, Any]:
        scenario_type = normalize_scenario(scenario)
        query_text = query.strip()
        result = await self.impact_service.analyze(
            query=query_text,
            repo_id=repo_id,
            max_depth=max_depth,
            direction=direction,
            db=db,
            natural_language=natural_language,
            scenario=scenario_type,
        )

        target_id = result.source_node["id"] if result.source_node else repo_id
        failure_probability = await self.calculate_failure_probability(result, repo_id, db)
        degradation_probability = self.calculate_degradation_probability(
            failure_probability, result.risk_score
        )
        evidence_chains = await self._load_evidence_chains(repo_id, result.source_node, db)
        workflow_impacts = self._simulate_workflows(result, failure_probability)
        service_impacts = self._simulate_services(result, workflow_impacts, failure_probability)
        journey_impacts = self._simulate_journeys(result, workflow_impacts, failure_probability)
        critical_paths = self._simulate_critical_paths(result, repo_id, db)
        recovery = self.recovery_complexity.estimate(
            dependency_count=len(result.impacted_nodes),
            critical_path_count=len(critical_paths),
            workflow_reach=len(result.workflow_impact),
            service_count=len(service_impacts),
        )
        deployment = self.deployment_safety.assess(
            failure_probability, result.risk_score, scenario_type
        )
        recommendation = self._recommendation(scenario_type, failure_probability, result)

        output = {
            "simulation_id": None,
            "query": query_text,
            "scenario": scenario_type,
            "target": result.source_node["name"] if result.source_node else "unknown",
            "risk_score": result.risk_score,
            "failure_probability": failure_probability,
            "degradation_probability": degradation_probability,
            "deployment_safety": deployment["status"],
            "deployment_recommendations": deployment["recommendations"],
            "deployment_reason": deployment["reason"],
            "affected_functions": [n.name for n in result.impacted_nodes[:20]],
            "affected_files": list({n.file_path for n in result.impacted_nodes if n.file_path})[:20],
            "affected_apis": [n.route_path or n.name for n in result.impacted_nodes if n.node_type == "api_route"],
            "affected_workflows": workflow_impacts,
            "affected_services": service_impacts,
            "affected_journeys": journey_impacts,
            "critical_paths": critical_paths,
            "recovery_complexity": recovery,
            "evidence_chains": evidence_chains,
            "recommendation": recommendation,
            "confidence": result.confidence,
            "risk_category": result.risk_level,
            "affected_nodes": [n.id for n in result.impacted_nodes[:50]],
        }

        profile_id = await self._persist_simulation(repo_id, target_id, scenario_type, output, result.risk_score, db)
        output["simulation_id"] = str(profile_id)
        await self._persist_impacts(profile_id, output, db)
        await self._persist_history(repo_id, query_text, scenario_type, output, db)
        return output

    async def simulate_delete(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self.simulate(*args, **kwargs)

    async def simulate_modify(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self.simulate(*args, **kwargs)

    async def simulate_refactor(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self.simulate(*args, **kwargs)

    async def simulate_rename(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self.simulate(*args, **kwargs)

    async def simulate_move(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self.simulate(*args, **kwargs)

    async def simulate_api_change(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self.simulate(*args, **kwargs)

    async def simulate_database_change(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self.simulate(*args, **kwargs)

    async def simulate_service_change(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self.simulate(*args, **kwargs)

    async def simulate_workflow_change(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self.simulate(*args, **kwargs)

    async def calculate_failure_probability(
        self, result: Any, repo_id: str, db: AsyncSession
    ) -> int:
        blast_radius_score = getattr(result.blast_radius, "blast_radius_score", 0) or 0
        centrality = sum((n.risk_score for n in result.impacted_nodes)) / max(1, len(result.impacted_nodes)) * 100
        workflow_reach = len(result.workflow_impact)
        api_count = len([n for n in result.impacted_nodes if n.node_type == "api_route"])
        critical_paths = len(getattr(result.blast_radius_report, "critical_paths_impacted", []))
        return self.failure_probability.estimate(
            risk_score=result.risk_score,
            blast_radius_score=blast_radius_score,
            critical_paths=critical_paths,
            centrality=min(100.0, centrality),
            workflow_reach=workflow_reach,
            api_count=api_count,
        )

    def calculate_degradation_probability(self, failure_probability: int, risk_score: float) -> int:
        return self.failure_probability.degradation_probability(failure_probability, risk_score)

    def generate_simulation_result(self, content: dict[str, Any]) -> dict[str, Any]:
        return content

    async def _load_evidence_chains(self, repo_id: str, source_node: dict | None, db: AsyncSession) -> list[dict[str, Any]]:
        statement = select(EvidenceChain).where(EvidenceChain.repo_id == UUID(repo_id))
        rows = (await db.execute(statement)).scalars().all()
        return [
            {
                "summary": row.summary,
                "target_type": row.target_type,
                "confidence_percent": round(float(row.confidence) * 100, 1),
                "steps": row.steps,
            }
            for row in rows[:20]
        ]

    def _simulate_workflows(self, result: Any, failure_probability: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for workflow in result.workflow_impact:
            severity = self.classifier.classify_workflow(workflow.confidence, failure_probability)
            out.append(
                {
                    "workflow_name": workflow.workflow_name,
                    "severity": severity,
                    "confidence": workflow.confidence,
                    "reason": workflow.user_impact,
                }
            )
        return out

    def _simulate_services(
        self, result: Any, workflow_impacts: list[dict[str, Any]], failure_probability: int
    ) -> list[dict[str, Any]]:
        impacted_workflows = len(workflow_impacts)
        return self.service_failure.assess_services(
            services=result.affected_systems,
            impacted_workflows=impacted_workflows,
            failure_probability=failure_probability,
        )

    def _simulate_journeys(
        self, result: Any, workflow_impacts: list[dict[str, Any]], failure_probability: int
    ) -> list[dict[str, Any]]:
        journey_names = result.affected_journeys or journey_names_for_workflows({w["workflow_name"] for w in workflow_impacts})
        return self.journey_failure.assess_journeys(
            journeys=journey_names,
            impacted_workflow_count=len(workflow_impacts),
            failure_probability=failure_probability,
        )

    def _simulate_critical_paths(self, result: Any, repo_id: str, db: AsyncSession) -> list[dict[str, Any]]:
        if not result.source_node:
            return []
        paths = await self.critical_path.list_paths(UUID(repo_id), db)
        impacted = self.critical_path.paths_impacted(
            paths,
            {n.id for n in result.impacted_nodes},
            result.source_node["id"],
        )
        return impacted

    def _recommendation(self, scenario: str, failure_probability: int, result: Any) -> str:
        if scenario == "delete" and failure_probability >= 75:
            return "Do not merge. Replace behind feature flag and run regression tests."
        if failure_probability >= 80:
            return "Block deployment until the impacted workflows and services are stabilized."
        if failure_probability >= 60:
            return "Use canary deployment and regression testing before merging."
        if failure_probability >= 35:
            return "Deploy behind a feature flag and monitor impacted APIs."
        return "Safe to deploy with standard validation and monitoring."

    async def _persist_simulation(
        self,
        repo_id: str,
        target_entity_id: str,
        scenario_type: str,
        output: dict[str, Any],
        risk_score: float,
        db: AsyncSession,
    ) -> UUID:
        profile = SimulationProfile(
            repo_id=UUID(repo_id),
            target_entity_id=UUID(target_entity_id),
            scenario_type=scenario_type,
            simulation_result=output,
            risk_score=risk_score,
        )
        db.add(profile)
        await db.flush()
        return profile.id

    async def _persist_impacts(self, simulation_id: UUID, output: dict[str, Any], db: AsyncSession) -> None:
        for workflow in output["affected_workflows"]:
            db.add(
                SimulationImpact(
                    simulation_id=simulation_id,
                    impact_type="workflow",
                    entity_type="workflow",
                    entity_id=workflow["workflow_name"],
                    severity=workflow["severity"],
                    evidence={"confidence": workflow["confidence"]},
                )
            )
        for service in output["affected_services"]:
            db.add(
                SimulationImpact(
                    simulation_id=simulation_id,
                    impact_type="service",
                    entity_type="service",
                    entity_id=service["service_name"],
                    severity=service["severity"],
                    evidence={"reason": service["reason"]},
                )
            )
        for journey in output["affected_journeys"]:
            db.add(
                SimulationImpact(
                    simulation_id=simulation_id,
                    impact_type="journey",
                    entity_type="journey",
                    entity_id=journey["journey_name"],
                    severity=journey["severity"],
                    evidence={"reason": journey["reason"]},
                )
            )
        for path in output["critical_paths"]:
            db.add(
                SimulationImpact(
                    simulation_id=simulation_id,
                    impact_type="critical_path",
                    entity_type="critical_path",
                    entity_id=path["id"],
                    severity=path["criticality"].upper(),
                    evidence={"impacted_nodes": path["impacted_node_names"]},
                )
            )
        await db.flush()

    async def _persist_history(
        self,
        repo_id: str,
        query: str,
        scenario_type: str,
        output: dict[str, Any],
        db: AsyncSession,
    ) -> None:
        db.add(
            SimulationHistory(
                repo_id=UUID(repo_id),
                query=query,
                scenario_type=scenario_type,
                result=output,
            )
        )
        await db.flush()
