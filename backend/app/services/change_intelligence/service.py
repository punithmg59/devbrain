import logging
import time
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repo import Repo
from app.services.intent.intent_engine import IntentEngine
from app.services.intent.schemas import IntentRequest
from app.services.entity_resolution.entity_resolver import EntityResolver
from app.services.reasoning.reasoning_engine import ReasoningEngine
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.report.report_composer import ReportComposer
from app.services.engineering_evidence.pipeline_integration import EngineeringEvidenceService
from app.services.change_intelligence.schemas import ChangeIntelligenceRequest, ChangeIntelligenceResponse, ChangeIntelligenceError
from app.services.report.schemas.engineering_report import EngineeringReport
from app.utils.errors import DevBrainException

logger = logging.getLogger(__name__)


class ChangeIntelligenceService:
    """Thin orchestration layer for the AI Change Intelligence pipeline."""

    def __init__(
        self,
        intent_engine: Optional[IntentEngine] = None,
        entity_resolver: Optional[EntityResolver] = None,
        evidence_service: Optional[EngineeringEvidenceService] = None,
        reasoning_engine: Optional[ReasoningEngine] = None,
        report_composer: Optional[ReportComposer] = None,
    ) -> None:
        self.intent_engine = intent_engine or IntentEngine()
        self.entity_resolver = entity_resolver or EntityResolver()
        self.evidence_service = evidence_service or EngineeringEvidenceService()
        self.reasoning_engine = reasoning_engine or ReasoningEngine()
        self.report_composer = report_composer or ReportComposer()

    async def analyze_change(self, repo: Repo, request: ChangeIntelligenceRequest, db: AsyncSession) -> ChangeIntelligenceResponse:
        if not request.question or not request.question.strip():
            raise DevBrainException("Question cannot be empty", 400, "EMPTY_QUESTION")

        if repo.analysis_status != "completed":
            raise DevBrainException("Repository analysis not complete", 400, "REPOSITORY_NOT_ANALYZED")

        timing: Dict[str, float] = {}
        start = time.perf_counter()

        # ── Stage 1: Intent Classification ─────────────────────────────────
        try:
            intent_request = IntentRequest(repo_id=str(repo.id), question=request.question)
            intent_start = time.perf_counter()
            intent_response = self.intent_engine.classify(intent_request)
            timing["intent_ms"] = (time.perf_counter() - intent_start) * 1000
            logger.info("change_intelligence intent repo_id=%s intent=%s confidence=%.2f", repo.id, intent_response.intent.intent, intent_response.intent.confidence)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("change_intelligence intent failed repo_id=%s", repo.id)
            raise DevBrainException("Unable to classify question", 502, "INTENT_ENGINE_FAILED") from exc

        # ── Stage 2: Resolve target name & type ────────────────────────────
        intent = intent_response.intent
        target_name = intent.target_name
        target_type = intent.target_type if hasattr(intent, "target_type") else "unknown"
        # Convert enum to string if needed
        if hasattr(target_type, "value"):
            target_type = target_type.value

        # If IntentEngine couldn't extract a proper entity name, fall back to
        # EntityResolver which does regex-based extraction from the raw question.
        _needs_resolution = (
            not target_name
            or target_name.lower() == "unknown"
            or target_name.strip() == request.question.strip()
        )

        if _needs_resolution:
            try:
                resolve_start = time.perf_counter()
                node, action, resolution = await self.entity_resolver.resolve_with_action(
                    db=db,
                    repo_id=str(repo.id),
                    query=request.question,
                )
                timing["entity_resolution_ms"] = (time.perf_counter() - resolve_start) * 1000

                if resolution.success and node:
                    target_name = node.name
                    target_type = node.node_type.value if hasattr(node.node_type, "value") else str(node.node_type)
                    logger.info(
                        "change_intelligence entity_resolution resolved %r → %r (%s) via %s",
                        request.question, target_name, target_type, resolution.match_type,
                    )
                else:
                    # Keep the intent's target_name — evidence will still collect
                    # repository-level data even without an exact node match.
                    logger.warning(
                        "change_intelligence entity_resolution found no match for %r, "
                        "proceeding with intent target_name=%r",
                        request.question, target_name,
                    )
            except Exception as exc:
                logger.warning("change_intelligence entity_resolution failed, continuing: %s", exc)

        # ── Stage 3: Evidence Collection ───────────────────────────────────
        try:
            evidence_start = time.perf_counter()
            evidence = await self.evidence_service.generate_evidence(
                repo_id=repo.id,
                target_name=target_name,
                target_type=target_type,
                db=db,
            )
            timing["evidence_ms"] = (time.perf_counter() - evidence_start) * 1000
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("change_intelligence evidence failed repo_id=%s", repo.id)
            raise DevBrainException("Unable to collect evidence", 502, "EVIDENCE_ENGINE_FAILED") from exc

        # ── Stage 4: Reasoning ─────────────────────────────────────────────
        try:
            reasoning_start = time.perf_counter()
            decision = self.reasoning_engine.reason(intent_response.intent, evidence)
            timing["reasoning_ms"] = (time.perf_counter() - reasoning_start) * 1000
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("change_intelligence reasoning failed repo_id=%s", repo.id)
            raise DevBrainException("Unable to generate decision", 502, "REASONING_ENGINE_FAILED") from exc

        # ── Stage 5: Report Composition ────────────────────────────────────
        try:
            report_start = time.perf_counter()
            report = self.report_composer.compose(intent_response.intent, decision, evidence)
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
