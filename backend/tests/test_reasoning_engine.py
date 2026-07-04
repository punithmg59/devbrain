import pytest
import uuid

from app.services.intent.schemas import Intent, IntentType, TargetType
from app.services.repository_intelligence.schemas import (
    EngineeringEvidence,
    EvidenceCollection,
    EvidenceCategory,
    EvidenceItem,
    WorkflowEvidenceItem,
    EvidenceScore,
    EvidenceMetadata,
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
    
    collection = EvidenceCollection()
    
    for i in range(callers):
        item = EvidenceItem(
            node_id=uuid.uuid4(),
            name=f"Caller{i}",
            node_type="class",
            full_path="a",
            category=EvidenceCategory.CALLER,
            relevance_score=0.9
        )
        collection.add(EvidenceCategory.CALLER, item)
        
    for i in range(dependents):
        item = EvidenceItem(
            node_id=uuid.uuid4(),
            name=f"Dependent{i}",
            node_type="class",
            full_path="b",
            category=EvidenceCategory.DEPENDENT,
            relevance_score=0.9
        )
        collection.add(EvidenceCategory.DEPENDENT, item)
        
    for i in range(integration_points):
        item = EvidenceItem(
            node_id=uuid.uuid4(),
            name=f"Module{i}",
            node_type="module",
            full_path="c",
            category=EvidenceCategory.INTEGRATION_POINT,
            relevance_score=0.8
        )
        collection.add(EvidenceCategory.INTEGRATION_POINT, item)
        
    if has_workflows:
        wf_criticality = "high" if critical_workflows else "medium"
        collection.add_workflow(
            WorkflowEvidenceItem(
                workflow_id=uuid.uuid4(),
                name="WF1",
                workflow_type="auth",
                criticality=wf_criticality,
                relevance_score=0.9
            )
        )
        
    score = EvidenceScore(
        overall_confidence=0.8,
        coverage_score=0.9,
        density_score=0.7,
        relevance_score=0.8
    )
    
    metadata = EvidenceMetadata()
    
    return EngineeringEvidence(
        intent_type=intent_type,
        target_name=target_name,
        target_type=target_type,
        repo_id=repo_id,
        evidence=collection,
        score=score,
        metadata=metadata,
        has_callers=callers > 0,
        has_callees=False,
        has_tests=has_tests,
        has_apis=has_apis,
        has_database=has_database,
        has_workflows=has_workflows,
        has_critical_paths=False,
    )


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
    
    # High risk profile: > 20 callers (40), has_database (25), has_workflows+critical (35), service (15) = 115 -> capped at 100 (CRITICAL)
    evidence = create_mock_evidence(
        intent_type="DELETE",
        target_name="UserService",
        target_type="service",
        callers=25,
        has_database=True,
        has_workflows=True,
        critical_workflows=True,
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
        has_workflows=False,
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
    
    decision = engine.reason(intent, evidence)
    
    assert decision.confidence == 0.68
