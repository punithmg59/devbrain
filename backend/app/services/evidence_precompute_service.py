"""Precompute and persist evidence chains for repository analysis."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import EvidenceChain, EvidenceRelationship, Workflow
from app.services.evidence_explainer import EvidenceExplainer
from app.services.journey_service import journey_names_for_workflows
from app.services.service_mapper import map_workflow_to_service

logger = logging.getLogger(__name__)


class EvidencePrecomputeService:
    def __init__(self) -> None:
        self.explainer = EvidenceExplainer()

    async def recompute_for_repo(self, repo_id: UUID, db: AsyncSession) -> dict[str, int]:
        await db.execute(delete(EvidenceChain).where(EvidenceChain.repo_id == repo_id))
        await db.execute(delete(EvidenceRelationship).where(EvidenceRelationship.repo_id == repo_id))

        workflows = await self._load_workflows(repo_id, db)
        workflow_names = [wf.name for wf in workflows]
        journey_map = {wf.name: journey_names_for_workflows({wf.name}) for wf in workflows}

        chain_count = 0
        relationship_count = 0

        for wf in workflows:
            if not wf.nodes:
                continue

            workflow_relationships = self._build_workflow_relationships(wf)
            for rel in workflow_relationships:
                db.add(EvidenceRelationship(**rel))
                relationship_count += 1

            if wf.services:
                service_name = wf.services[0].service_name
            else:
                service_name = map_workflow_to_service(wf.name)

            workflow_chain = self.explainer.build_chain(
                source_name="repository",
                steps=[(wf.name, "workflow")],
                target_label=service_name,
                target_type="service",
                confidence=wf.confidence,
            )
            db.add(
                EvidenceChain(
                    repo_id=repo_id,
                    source_node_id=None,
                    target_type="service",
                    target_id=service_name,
                    chain_type="service",
                    summary=workflow_chain["summary"],
                    confidence=float(workflow_chain["confidence_percent"]) / 100.0,
                    steps=workflow_chain["steps"],
                )
            )
            chain_count += 1

            for journey_name in journey_map.get(wf.name, []):
                journey_chain = self.explainer.build_chain(
                    source_name="repository",
                    steps=[(wf.name, "workflow")],
                    target_label=journey_name,
                    target_type="journey",
                    confidence=0.9,
                )
                db.add(
                    EvidenceChain(
                        repo_id=repo_id,
                        source_node_id=None,
                        target_type="journey",
                        target_id=journey_name,
                        chain_type="journey",
                        summary=journey_chain["summary"],
                        confidence=float(journey_chain["confidence_percent"]) / 100.0,
                        steps=journey_chain["steps"],
                    )
                )
                chain_count += 1

            for api in wf.apis:
                api_chain = self.explainer.build_chain(
                    source_name="repository",
                    steps=[(wf.name, "workflow")],
                    target_label=api.api_route,
                    target_type="api_route",
                    confidence=0.75,
                )
                db.add(
                    EvidenceChain(
                        repo_id=repo_id,
                        source_node_id=None,
                        target_type="api_route",
                        target_id=api.api_route,
                        chain_type="api_route",
                        summary=api_chain["summary"],
                        confidence=float(api_chain["confidence_percent"]) / 100.0,
                        steps=api_chain["steps"],
                    )
                )
                chain_count += 1

        await db.flush()
        logger.info(
            "Precomputed %d evidence chains and %d relationships for repo %s",
            chain_count,
            relationship_count,
            repo_id,
        )
        return {
            "chains": chain_count,
            "relationships": relationship_count,
        }

    async def _load_workflows(self, repo_id: UUID, db: AsyncSession) -> list[Workflow]:
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

    def _build_workflow_relationships(self, workflow: Workflow) -> list[dict[str, Any]]:
        relationships: list[dict[str, Any]] = []
        for node in workflow.nodes:
            relationships.append(
                {
                    "repo_id": workflow.repo_id,
                    "source_type": "workflow",
                    "source_id": str(workflow.id),
                    "target_type": "node",
                    "target_id": str(node.node_id),
                    "relationship_type": "contains",
                    "evidence": {
                        "workflow_name": workflow.name,
                        "node_id": str(node.node_id),
                    },
                }
            )
        for service in workflow.services:
            relationships.append(
                {
                    "repo_id": workflow.repo_id,
                    "source_type": "workflow",
                    "source_id": str(workflow.id),
                    "target_type": "service",
                    "target_id": service.service_name,
                    "relationship_type": "supports",
                    "evidence": {
                        "workflow_name": workflow.name,
                        "service_name": service.service_name,
                    },
                }
            )
        for api in workflow.apis:
            relationships.append(
                {
                    "repo_id": workflow.repo_id,
                    "source_type": "workflow",
                    "source_id": str(workflow.id),
                    "target_type": "api_route",
                    "target_id": api.api_route,
                    "relationship_type": "exposes",
                    "evidence": {
                        "workflow_name": workflow.name,
                        "api_route": api.api_route,
                    },
                }
            )
        for journey_name in journey_names_for_workflows({workflow.name}):
            relationships.append(
                {
                    "repo_id": workflow.repo_id,
                    "source_type": "workflow",
                    "source_id": str(workflow.id),
                    "target_type": "journey",
                    "target_id": journey_name,
                    "relationship_type": "participates_in",
                    "evidence": {
                        "workflow_name": workflow.name,
                        "journey_name": journey_name,
                    },
                }
            )
        return relationships
