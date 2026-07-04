import logging
import time
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.engineering_report import EngineeringReport
from app.services.intent_engine import IntentEngine
from app.services.repository_evidence_engine import RepositoryEvidenceEngine
from app.services.impact_analysis_engine import ImpactAnalysisEngine
from app.services.recommendation_engine import RecommendationEngine

from app.schemas.evidence import EvidenceRequest
from app.schemas.impact_analysis import ImpactAnalysisRequest
from app.schemas.recommendation import RecommendationRequest


logger = logging.getLogger(__name__)


class AIChangePipelineService:
    """
    Core Orchestration Service for DevBrain.
    Connects the Intent, Evidence, Impact, and Recommendation engines into a single pipeline.
    """

    def __init__(
        self,
        intent_engine: IntentEngine,
        evidence_engine: RepositoryEvidenceEngine,
        impact_engine: ImpactAnalysisEngine,
        recommendation_engine: RecommendationEngine,
    ):
        self.intent_engine = intent_engine
        self.evidence_engine = evidence_engine
        self.impact_engine = impact_engine
        self.recommendation_engine = recommendation_engine

    async def generate_engineering_report(
        self, question: str, repo_id: UUID, db: AsyncSession
    ) -> EngineeringReport:
        """
        Executes the AI Change Intelligence Pipeline.
        """
        execution_metrics = {}
        pipeline_start = time.perf_counter()

        # 1. Intent Engine
        t0 = time.perf_counter()
        try:
            intent_response = self.intent_engine.classify(question)
            execution_metrics["intent_engine_ms"] = (time.perf_counter() - t0) * 1000
        except Exception as e:
            logger.error(f"IntentEngine failed: {e}", exc_info=True)
            raise RuntimeError(f"Pipeline failed at Intent classification: {e}")

        # 2. Evidence Engine
        t0 = time.perf_counter()
        evidence_response = None
        try:
            target_name = intent_response.target_name or question
            evidence_req = EvidenceRequest(
                intent=intent_response.intent,
                repo_id=repo_id,
                target=target_name,
                max_results=50,
            )
            evidence_response = await self.evidence_engine.collect_evidence(evidence_req, db)
            execution_metrics["evidence_engine_ms"] = (time.perf_counter() - t0) * 1000
        except Exception as e:
            logger.error(f"EvidenceEngine failed: {e}", exc_info=True)
            # Evidence can fail, but we might still try impact if we have target_name
            execution_metrics["evidence_engine_ms"] = (time.perf_counter() - t0) * 1000

        # 3. Impact Engine
        t0 = time.perf_counter()
        impact_response = None
        try:
            target_node_id = None
            if evidence_response and evidence_response.target_node:
                target_node_id = evidence_response.target_node.id

            impact_req = ImpactAnalysisRequest(
                repo_id=repo_id,
                intent=intent_response.intent,
                target=intent_response.target_name or question,
                target_node_id=target_node_id,
                max_depth=5,
                include_indirect=True,
            )
            impact_response = await self.impact_engine.analyze_impact(impact_req, db)
            execution_metrics["impact_engine_ms"] = (time.perf_counter() - t0) * 1000
        except Exception as e:
            logger.error(f"ImpactAnalysisEngine failed: {e}", exc_info=True)
            execution_metrics["impact_engine_ms"] = (time.perf_counter() - t0) * 1000

        # 4. Recommendation Engine
        t0 = time.perf_counter()
        recommendation_response = None
        try:
            rec_req = RecommendationRequest(
                intent=intent_response.intent,
                target=intent_response.target_name or question,
                evidence=evidence_response,
                impact=impact_response,
                include_tests=True,
                include_rollback=True,
            )
            recommendation_response = self.recommendation_engine.generate_recommendations(rec_req)
            execution_metrics["recommendation_engine_ms"] = (time.perf_counter() - t0) * 1000
        except Exception as e:
            logger.error(f"RecommendationEngine failed: {e}", exc_info=True)
            execution_metrics["recommendation_engine_ms"] = (time.perf_counter() - t0) * 1000

        execution_metrics["total_pipeline_ms"] = (time.perf_counter() - pipeline_start) * 1000

        # Compile final report
        return EngineeringReport(
            question=question,
            intent=intent_response,
            evidence=evidence_response,
            impact=impact_response,
            recommendations=recommendation_response,
            execution_metrics=execution_metrics,
        )
