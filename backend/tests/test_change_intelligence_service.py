from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.repo import Repo
from app.services.change_intelligence.schemas import ChangeIntelligenceRequest
from app.services.change_intelligence.service import ChangeIntelligenceService
from app.services.intent.schemas import Intent, IntentType, TargetType
from app.services.reasoning.schemas.engineering_decision import DecisionType, EngineeringDecision, RiskLevel
from app.services.report.schemas.engineering_report import EngineeringReport
from app.utils.errors import DevBrainException


class StubIntentEngine:
    def __init__(self, result):
        self.result = result

    def classify(self, request):
        return self.result


class StubEvidenceEngine:
    def __init__(self, result):
        self.result = result

    async def collect_evidence(self, repo_id, intent, db):
        return self.result


class StubReasoningEngine:
    def __init__(self, result):
        self.result = result

    def reason(self, intent, evidence):
        return self.result


class StubReportComposer:
    def __init__(self, result):
        self.result = result

    def compose(self, intent, decision):
        return self.result


@pytest.fixture
def repo() -> Repo:
    return Repo(
        id=uuid4(),
        user_id=uuid4(),
        github_repo_id=123,
        full_name="demo/repo",
        name="repo",
        analysis_status="completed",
    )


@pytest.mark.asyncio
async def test_successful_request_returns_report(repo):
    intent = SimpleNamespace(
        intent=IntentType.DELETE,
        target_name="AuthService",
        confidence=0.91,
        target_type=TargetType.SERVICE,
    )
    intent_response = SimpleNamespace(intent=intent, processing_time_ms=10.0)
    decision = EngineeringDecision(
        decision=DecisionType.DO_NOT_DELETE,
        risk_level=RiskLevel.HIGH,
        risk_score=92,
        confidence=0.97,
        summary="Do not delete",
        primary_reason="Has dependents",
    )
    report = EngineeringReport(
        title="Delete Report",
        intent="DELETE",
        hero={"verdict": "Do not delete", "risk_level": "HIGH", "risk_score": 92, "confidence": 0.97},
        sections=[],
    )

    service = ChangeIntelligenceService(
        intent_engine=StubIntentEngine(intent_response),
        evidence_engine=StubEvidenceEngine(object()),
        reasoning_engine=StubReasoningEngine(decision),
        report_composer=StubReportComposer(report),
    )

    response = await service.analyze_change(repo, ChangeIntelligenceRequest(question="What breaks if I delete AuthService?"), db=None)

    assert response.report["title"] == "Delete Report"
    assert response.timing["total_ms"] >= 0
    assert response.timing["intent_ms"] >= 0


@pytest.mark.asyncio
async def test_empty_question_raises_validation_error(repo):
    service = ChangeIntelligenceService()

    with pytest.raises(DevBrainException) as excinfo:
        await service.analyze_change(repo, ChangeIntelligenceRequest(question="   "), db=None)

    assert excinfo.value.code == "EMPTY_QUESTION"


@pytest.mark.asyncio
async def test_repository_not_analyzed_raises_error(repo):
    repo.analysis_status = "pending"
    service = ChangeIntelligenceService()

    with pytest.raises(DevBrainException) as excinfo:
        await service.analyze_change(repo, ChangeIntelligenceRequest(question="What breaks if I delete AuthService?"), db=None)

    assert excinfo.value.code == "REPOSITORY_NOT_ANALYZED"


@pytest.mark.asyncio
async def test_engine_failure_propagates(repo):
    service = ChangeIntelligenceService(
        intent_engine=StubIntentEngine(Exception("boom")),
        evidence_engine=StubEvidenceEngine(object()),
        reasoning_engine=StubReasoningEngine(EngineeringDecision(
            decision=DecisionType.DO_NOT_DELETE,
            risk_level=RiskLevel.HIGH,
            risk_score=92,
            confidence=0.97,
            summary="Do not delete",
            primary_reason="Has dependents",
        )),
        report_composer=StubReportComposer(EngineeringReport(
            title="Delete Report",
            intent="DELETE",
            hero={"verdict": "Do not delete", "risk_level": "HIGH", "risk_score": 92, "confidence": 0.97},
            sections=[],
        )),
    )

    with pytest.raises(DevBrainException) as excinfo:
        await service.analyze_change(repo, ChangeIntelligenceRequest(question="What breaks if I delete AuthService?"), db=None)

    assert excinfo.value.code == "INTENT_ENGINE_FAILED"
