import logging
import time
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repo import Repo
from app.services.intent.intent_engine import IntentEngine
from app.services.intent.schemas import IntentRequest
from app.services.reasoning.reasoning_engine import ReasoningEngine
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.report.report_composer import ReportComposer
from app.services.repository_intelligence.repository_intelligence_engine import RepositoryIntelligenceEngine
from app.services.change_intelligence.schemas import ChangeIntelligenceRequest, ChangeIntelligenceResponse, ChangeIntelligenceError
from app.services.report.schemas.engineering_report import EngineeringReport
from app.utils.errors import DevBrainException

logger = logging.getLogger(__name__)


class ChangeIntelligenceService:
    """Thin orchestration layer for the AI Change Intelligence pipeline."""

    def __init__(
        self,
        intent_engine: Optional[IntentEngine] = None,
        evidence_engine: Optional[RepositoryIntelligenceEngine] = None,
        reasoning_engine: Optional[ReasoningEngine] = None,
        report_composer: Optional[ReportComposer] = None,
    ) -> None:
        self.intent_engine = intent_engine or IntentEngine()
        self.evidence_engine = evidence_engine or RepositoryIntelligenceEngine()
        self.reasoning_engine = reasoning_engine or ReasoningEngine()
        self.report_composer = report_composer or ReportComposer()

    async def analyze_change(self, repo: Repo, request: ChangeIntelligenceRequest, db: AsyncSession) -> ChangeIntelligenceResponse:
        if not request.question or not request.question.strip():
            raise DevBrainException("Question cannot be empty", 400, "EMPTY_QUESTION")

        if repo.analysis_status != "completed":
            raise DevBrainException("Repository analysis not complete", 400, "REPOSITORY_NOT_ANALYZED")

        timing: Dict[str, float] = {}
        start = time.perf_counter()

        try:
            intent_request = IntentRequest(repo_id=str(repo.id), question=request.question)
            intent_start = time.perf_counter()
            intent_response = self.intent_engine.classify(intent_request)
            timing["intent_ms"] = (time.perf_counter() - intent_start) * 1000
            logger.info("change_intelligence intent repo_id=%s intent=%s confidence=%.2f", repo.id, intent_response.intent.intent, intent_response.intent.confidence)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("change_intelligence intent failed repo_id=%s", repo.id)
            raise DevBrainException("Unable to classify question", 502, "INTENT_ENGINE_FAILED") from exc

        try:
            evidence_start = time.perf_counter()
            evidence = await self.evidence_engine.collect_evidence(repo.id, intent_response.intent, db)
            timing["evidence_ms"] = (time.perf_counter() - evidence_start) * 1000
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("change_intelligence evidence failed repo_id=%s", repo.id)
            raise DevBrainException("Unable to collect evidence", 502, "EVIDENCE_ENGINE_FAILED") from exc

        try:
            reasoning_start = time.perf_counter()
            decision = self.reasoning_engine.reason(intent_response.intent, evidence)
            timing["reasoning_ms"] = (time.perf_counter() - reasoning_start) * 1000
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("change_intelligence reasoning failed repo_id=%s", repo.id)
            raise DevBrainException("Unable to generate decision", 502, "REASONING_ENGINE_FAILED") from exc

        try:
            report_start = time.perf_counter()
            report = self.report_composer.compose(intent_response.intent, decision)
            timing["report_ms"] = (time.perf_counter() - report_start) * 1000
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("change_intelligence report failed repo_id=%s", repo.id)
            raise DevBrainException("Unable to compose report", 502, "REPORT_COMPOSER_FAILED") from exc

        timing["total_ms"] = (time.perf_counter() - start) * 1000

        return ChangeIntelligenceResponse(
            report=report.model_dump(),
            timing=timing,
            generated_at=report.generated_at,
        )
