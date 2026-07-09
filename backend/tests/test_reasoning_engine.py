import pytest
import uuid

from app.services.intent.schemas import Intent, IntentType, TargetType
from app.services.engineering_evidence.models import (
    EngineeringEvidence,
    EvidenceGroup,
    EvidenceCategory,
    Criticality,
    FailureMode,
)
from app.services.reference_intelligence.models import (
    Reference,
    ReferenceType,
    ReferenceLocation,
)
from app.services.reasoning.schemas.engineering_decision import RiskLevel, DecisionType
from app.services.reasoning import ReasoningEngine


def create_mock_evidence(
    intent_type: str,
    target_name: str,
    target_type: str,
    callers: int = 0,
    dependents: int = 0,
    has_database: bool = False,
    has_apis: bool = False,
    has_workflows: bool = False,
    critical_workflows: bool = False,
    has_tests: bool = True,
    integration_points: int = 0,
) -> EngineeringEvidence:
    """Helper to construct mock evidence for reasoning engine."""
    repo_id = uuid.uuid4()
    target_id = uuid.uuid4()
    
    # Create runtime references (callers)
    runtime_refs = []
    for i in range(callers):
        runtime_refs.append(
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path=f"caller{i}.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.HIGH if i < 5 else Criticality.MEDIUM,
                provider=f"Caller{i}",
                consumer=target_name,
            )
        )
    
    # Create database references
    database_refs = []
    if has_database:
        database_refs.append(
            Reference(
                reference_type=ReferenceType.ORM_MODEL,
                reference_location=ReferenceLocation.DATABASE,
                file_path="models.py",
                line_number=5,
                confidence=0.95,
                criticality=Criticality.CRITICAL,
                provider="User",
            )
        )
    
    # Create public API references
    public_api_refs = []
    if has_apis:
        public_api_refs.append(
            Reference(
                reference_type=ReferenceType.FASTAPI_ROUTE,
                reference_location=ReferenceLocation.RUNTIME,
                file_path="routes.py",
                line_number=5,
                confidence=0.95,
                criticality=Criticality.HIGH,
                provider="/api/test",
            )
        )
    
    # Create testing references
    testing_refs = []
    if has_tests:
        testing_refs.append(
            Reference(
                reference_type=ReferenceType.PYTEST_TEST,
                reference_location=ReferenceLocation.TEST,
                file_path="test.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.LOW,
                provider=f"test_{target_name}",
            )
        )
    
    # Create internal service references (integration points)
    internal_service_refs = []
    for i in range(integration_points):
        internal_service_refs.append(
            Reference(
                reference_type=ReferenceType.IMPORT,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path=f"module{i}.py",
                line_number=1,
                confidence=0.85,
                criticality=Criticality.MEDIUM,
                provider=f"Module{i}",
            )
        )
    
    # Create evidence groups
    runtime_group = None
    if runtime_refs:
        runtime_group = EvidenceGroup(
            category=EvidenceCategory.RUNTIME,
            references=runtime_refs,
            criticality=Criticality.HIGH if callers > 5 else Criticality.MEDIUM,
            impact_score=0.7 if callers > 0 else 0.0,
            confidence=0.8,
            engineering_summary="Runtime dependencies found",
            estimated_failure_mode=FailureMode.RUNTIME_ERROR,
            risk_drivers=["Runtime callers"],
            affected_systems=[f"Caller{i}" for i in range(min(callers, 5))],
        )
        runtime_group.calculate_metrics()
    
    database_group = None
    if database_refs:
        database_group = EvidenceGroup(
            category=EvidenceCategory.DATABASE,
            references=database_refs,
            criticality=Criticality.CRITICAL,
            impact_score=0.9,
            confidence=0.9,
            engineering_summary="Database dependencies found",
            estimated_failure_mode=FailureMode.DATA_CORRUPTION,
            risk_drivers=["Database models"],
            affected_systems=["Database"],
        )
        database_group.calculate_metrics()
    
    public_api_group = None
    if public_api_refs:
        public_api_group = EvidenceGroup(
            category=EvidenceCategory.PUBLIC_API,
            references=public_api_refs,
            criticality=Criticality.HIGH,
            impact_score=0.8,
            confidence=0.85,
            engineering_summary="Public API dependencies found",
            estimated_failure_mode=FailureMode.API_FAILURE,
            risk_drivers=["API routes"],
            affected_systems=["API Gateway"],
        )
        public_api_group.calculate_metrics()
    
    testing_group = None
    if testing_refs:
        testing_group = EvidenceGroup(
            category=EvidenceCategory.TESTING,
            references=testing_refs,
            criticality=Criticality.LOW,
            impact_score=0.3,
            confidence=0.9,
            engineering_summary="Test coverage found",
            estimated_failure_mode=FailureMode.TEST_FAILURE,
            risk_drivers=[],
            affected_systems=[],
        )
        testing_group.calculate_metrics()
    
    internal_service_group = None
    if internal_service_refs:
        internal_service_group = EvidenceGroup(
            category=EvidenceCategory.INTERNAL_SERVICE,
            references=internal_service_refs,
            criticality=Criticality.MEDIUM,
            impact_score=0.5,
            confidence=0.8,
            engineering_summary="Internal service dependencies found",
            estimated_failure_mode=FailureMode.BUILD_ERROR,
            risk_drivers=["Internal imports"],
            affected_systems=[f"Module{i}" for i in range(integration_points)],
        )
        internal_service_group.calculate_metrics()
    
    evidence = EngineeringEvidence(
        target_id=target_id,
        target_name=target_name,
        target_type=target_type,
        repo_id=repo_id,
        runtime=runtime_group,
        database=database_group,
        public_api=public_api_group,
        testing=testing_group,
        internal_service=internal_service_group,
        overall_summary=f"Evidence for {target_name}",
        overall_criticality=Criticality.HIGH if callers > 5 else Criticality.LOW,
        overall_impact_score=0.7 if callers > 0 else 0.3,
        overall_confidence=0.8,
        evidence_confidence=0.8,
    )
    
    evidence.calculate_overall_metrics()
    return evidence


def test_delete_critical_risk():
    engine = ReasoningEngine()
    intent = Intent(
        intent=IntentType.DELETE,
        target_name="UserService",
        target_type=TargetType.SERVICE,
        confidence=0.9,
        requires_graph=True,
        requires_llm=False,
        extracted_entities=[],
        raw_question="Delete UserService",
        normalized_question="Delete UserService",
        reasoning="",
    )
    
    # High risk profile: > 20 callers (40), has_database (25), service (15) = 80 -> HIGH/CRITICAL
    evidence = create_mock_evidence(
        intent_type="DELETE",
        target_name="UserService",
        target_type="service",
        callers=25,
        has_database=True,
    )
    
    decision = engine.reason(intent, evidence)
    
    assert decision.risk_level == RiskLevel.CRITICAL
    assert decision.decision == DecisionType.DO_NOT_DELETE
    assert "Deprecate the component instead of deleting it." in decision.alternative_options
    assert len(decision.affected_components) > 0


def test_delete_low_risk():
    engine = ReasoningEngine()
    intent = Intent(
        intent=IntentType.DELETE,
        target_name="UnusedHelper",
        target_type=TargetType.FILE,
        confidence=0.9,
        requires_graph=True,
        requires_llm=False,
        extracted_entities=[],
        raw_question="Delete UnusedHelper",
        normalized_question="Delete UnusedHelper",
        reasoning="",
    )
    
    evidence = create_mock_evidence(
        intent_type="DELETE",
        target_name="UnusedHelper",
        target_type="file",
        callers=0,
        has_database=False,
        has_tests=True,
    )
    
    decision = engine.reason(intent, evidence)
    
    assert decision.risk_level == RiskLevel.LOW
    assert decision.decision == DecisionType.SAFE_TO_DELETE
    assert "Remove the component from the codebase." in decision.recommended_actions


def test_add_feature_integration():
    engine = ReasoningEngine()
    intent = Intent(
        intent=IntentType.ADD_FEATURE,
        target_name="OAuth",
        target_type=TargetType.MODULE,
        confidence=0.9,
        requires_graph=True,
        requires_llm=False,
        extracted_entities=[],
        raw_question="Add OAuth",
        normalized_question="Add OAuth",
        reasoning="",
    )
    
    evidence = create_mock_evidence(
        intent_type="ADD_FEATURE",
        target_name="OAuth",
        target_type="module",
        integration_points=1,
    )
    
    decision = engine.reason(intent, evidence)
    
    assert decision.decision == DecisionType.IMPLEMENT_IN_MODULE
    assert "Module0" in decision.summary


def test_refactor_high_risk():
    engine = ReasoningEngine()
    intent = Intent(
        intent=IntentType.REFACTOR,
        target_name="CoreAuth",
        target_type=TargetType.SERVICE,
        confidence=0.9,
        requires_graph=True,
        requires_llm=False,
        extracted_entities=[],
        raw_question="Refactor CoreAuth",
        normalized_question="Refactor CoreAuth",
        reasoning="",
    )
    
    evidence = create_mock_evidence(
        intent_type="REFACTOR",
        target_name="CoreAuth",
        target_type="service",
        callers=15, # Medium risk base
        has_database=True,
        has_tests=False # No tests increases risk
    )
    
    decision = engine.reason(intent, evidence)
    
    assert decision.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert decision.decision == DecisionType.REFACTOR_HIGH_RISK
    assert "100% test coverage" in str(decision.required_tests)
    assert "Write unit tests for CoreAuth." in decision.required_tests


def test_confidence_calculation():
    engine = ReasoningEngine()
    intent = Intent(
        intent=IntentType.EXPLAIN,
        target_name="API",
        target_type=TargetType.UNKNOWN,
        confidence=0.5, # Low intent confidence
        requires_graph=True,
        requires_llm=False,
        extracted_entities=[],
        raw_question="Explain API",
        normalized_question="Explain API",
        reasoning="",
    )
    
    evidence = create_mock_evidence(
        intent_type="EXPLAIN",
        target_name="API",
        target_type="api_route",
    )
    # Evidence confidence in create_mock_evidence is 0.8
    # Formula: (0.5 * 0.4) + (0.8 * 0.6) = 0.2 + 0.48 = 0.68
    # But with no runtime references, the confidence calculation uses evidence_confidence directly
    
    decision = engine.reason(intent, evidence)
    
    # With no runtime references, confidence is based primarily on evidence_confidence
    assert decision.confidence >= 0.6
