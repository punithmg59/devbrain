import json

from app.services.intent.schemas import Intent, IntentType, TargetType
from app.services.reasoning.schemas.engineering_decision import DecisionType, EngineeringDecision, RiskLevel
from app.services.report.report_composer import ReportComposer
from app.services.report.schemas.engineering_report import EngineeringReport, HeroSectionModel


def _decision(**overrides) -> EngineeringDecision:
    base = {
        "decision": DecisionType.DO_NOT_DELETE,
        "risk_level": RiskLevel.HIGH,
        "risk_score": 92,
        "confidence": 0.97,
        "summary": "A deletion is risky and should be avoided.",
        "primary_reason": "The component has multiple dependents.",
        "affected_components": [
            {"name": "payments-api", "type": "service", "category": "backend"},
            {"name": "billing-worker", "type": "worker", "category": "async"},
        ],
        "recommended_actions": ["Review dependents", "Create migration plan"],
        "alternative_options": ["Defer removal", "Introduce compatibility layer"],
        "required_tests": ["Unit tests", "Integration tests"],
        "follow_up_questions": ["Do you want a rollback plan?"],
    }
    base.update(overrides)
    return EngineeringDecision(**base)


def _intent(intent_type: IntentType) -> Intent:
    return Intent(
        intent=intent_type,
        target_type=TargetType.SERVICE,
        target_name="payments-api",
        confidence=0.94,
        requires_graph=True,
        requires_llm=False,
        extracted_entities=[],
        raw_question="test",
        normalized_question="test",
        reasoning="test",
    )


def test_delete_report_uses_expected_sections_and_serializes_to_json():
    composer = ReportComposer()
    report = composer.compose(_intent(IntentType.DELETE), _decision())

    assert isinstance(report, EngineeringReport)
    assert isinstance(report.hero, HeroSectionModel)
    assert report.intent == IntentType.DELETE.value
    assert [section.type for section in report.sections] == [
        "hero",
        "summary",
        "impact",
        "evidence",
        "recommendations",
        "tests",
        "actions",
    ]

    payload = report.model_dump()
    assert payload["hero"]["risk_level"] == "HIGH"
    assert json.loads(report.model_dump_json())["title"] == report.title


def test_explain_report_uses_architecture_sections():
    composer = ReportComposer()
    report = composer.compose(_intent(IntentType.EXPLAIN), _decision())

    assert [section.type for section in report.sections] == ["hero", "architecture", "summary", "evidence"]
    assert report.sections[0].type == "hero"
    assert report.sections[1].title == "Architecture Overview"


def test_planning_report_uses_planning_sections():
    composer = ReportComposer()
    report = composer.compose(_intent(IntentType.PLANNING), _decision())

    assert [section.type for section in report.sections] == ["hero", "planning", "recommendations", "tests", "actions"]
    assert report.sections[1].type == "planning"


def test_architecture_report_uses_architecture_sections_in_order():
    composer = ReportComposer()
    report = composer.compose(_intent(IntentType.ARCHITECTURE), _decision())

    assert [section.type for section in report.sections] == ["hero", "architecture", "impact", "evidence"]
    assert [section.priority for section in report.sections] == [0, 15, 20, 30]


def test_missing_data_skips_empty_sections():
    composer = ReportComposer()
    report = composer.compose(
        _intent(IntentType.DELETE),
        _decision(
            affected_components=[],
            recommended_actions=[],
            alternative_options=[],
            required_tests=[],
            follow_up_questions=[],
        ),
    )

    assert [section.type for section in report.sections] == ["hero", "summary", "evidence"]
    assert report.next_actions == ["Review decision summary"]
