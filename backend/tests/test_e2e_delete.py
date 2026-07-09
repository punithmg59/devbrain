"""
End-to-end test for DELETE intent scenario.

Tests the complete pipeline from natural language question to engineering intelligence response
for delete operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from uuid import uuid4

from app.services.nlq_engine import NLQEngine
from app.services.intent.schemas import IntentType, TargetType
from app.services.engineering_evidence.models import EngineeringEvidence, ASTNode, DependencyGraph, CallGraph


@pytest.mark.asyncio
async def test_e2e_delete_intent():
    """
    End-to-end test for DELETE intent.
    
    Tests:
    - Intent classification
    - Entity resolution
    - Evidence collection
    - Evidence validation
    - Impact analysis
    - Engineering intelligence generation
    - Response structure
    """
    
    # Setup mock database session
    mock_db = AsyncMock()
    
    # Create NLQ Engine
    nlq_engine = NLQEngine(db=mock_db)
    
    # Mock intent engine
    mock_intent = MagicMock()
    mock_intent.intent = IntentType.DELETE
    mock_intent.target_type = TargetType.SERVICE
    mock_intent.target_name = "AuthService"
    mock_intent.confidence = 0.95
    mock_intent.requires_llm = False
    mock_intent.reasoning = "Classified as DELETE intent"
    mock_intent.extracted_entities = []
    
    mock_intent_response = MagicMock()
    mock_intent_response.intent = mock_intent
    mock_intent_response.processing_time_ms = 5.0
    
    nlq_engine.intent_engine.classify = Mock(return_value=mock_intent_response)
    
    # Mock entity resolver
    nlq_engine.entity_resolver.resolve = Mock(return_value={
        "node_id": str(uuid4()),
        "name": "AuthService",
        "type": "service"
    })
    
    # Mock repository data collector
    nlq_engine.repository_data_collector.collect_repository_data = AsyncMock(return_value={
        'ast_nodes': [
            ASTNode(node_type="class", name="AuthService", file_path="auth.py", line_number=10)
        ],
        'dependency_graph': DependencyGraph(
            nodes=["AuthService", "UserService", "PaymentService"],
            edges=[
                MagicMock(from_node="AuthService", to_node="UserService"),
                MagicMock(from_node="AuthService", to_node="PaymentService")
            ],
            total_nodes=3,
            total_edges=2
        ),
        'call_graph': CallGraph(function_calls=[], call_depth=0, entry_points=[]),
        'classes': [
            MagicMock(name="AuthService", file_path="auth.py"),
            MagicMock(name="UserService", file_path="user.py")
        ],
        'functions': [
            MagicMock(name="authenticate", file_path="auth.py"),
            MagicMock(name="authorize", file_path="auth.py")
        ],
        'api_routes': [
            MagicMock(path="/api/auth/login", file_path="auth.py"),
            MagicMock(path="/api/auth/logout", file_path="auth.py")
        ],
        'imports': [
            MagicMock(module="fastapi", file_path="auth.py"),
            MagicMock(module="sqlalchemy", file_path="auth.py")
        ]
    })
    
    # Mock impact analysis
    nlq_engine.impact_analysis.analyze_impact = Mock(return_value={
        "summary": "Deleting AuthService would break 3 components: UserService, PaymentService, and 2 API routes",
        "evidence": {
            "affected_components": ["UserService", "PaymentService"],
            "affected_api_routes": ["/api/auth/login", "/api/auth/logout"]
        },
        "processing_time_ms": 50.0
    })
    
    # Execute the test
    question = "What breaks if I delete AuthService?"
    repo_id = str(uuid4())
    
    result = await nlq_engine.process_question(
        repo_id=repo_id,
        question=question,
        db=mock_db
    )
    
    # Verify response structure
    assert result["question"] == question
    assert result["intent"] == "DELETE"
    assert result["target_name"] == "AuthService"
    assert result["confidence"] == 0.95
    assert result["grounded_in_repository"] == True
    
    # Verify engineering decision
    assert "engineering_decision" in result
    assert "delete" in result["engineering_decision"]["decision"].lower()
    assert result["engineering_decision"]["confidence"] > 0
    
    # Verify engineering evidence
    assert "engineering_evidence" in result
    assert result["engineering_evidence"]["evidence_confidence"] > 0
    assert len(result["engineering_evidence"]["data_sources"]) > 0
    
    # Verify repository analysis
    assert "repository_analysis" in result
    assert result["repository_analysis"]["structure_summary"]
    
    # Verify affected components
    assert "affected_components" in result
    assert len(result["affected_components"]) > 0
    
    # Verify risk assessment
    assert "risk_assessment" in result
    assert result["risk_assessment"]["overall_risk"] in ["critical", "high", "medium", "low"]
    
    # Verify recommended changes
    assert "recommended_changes" in result
    assert len(result["recommended_changes"]) > 0
    
    # Verify implementation plan
    assert "implementation_plan" in result
    assert len(result["implementation_plan"]["steps"]) > 0
    assert result["implementation_plan"]["total_estimated_time"]
    
    # Verify testing checklist
    assert "testing_checklist" in result
    assert result["testing_checklist"]["total_test_count"] > 0
    
    # Verify engineering actions
    assert "engineering_actions" in result
    assert len(result["engineering_actions"]) > 0
    
    # Verify no exceptions were raised
    assert "error" not in result
    
    print("✓ DELETE intent end-to-end test passed")


@pytest.mark.asyncio
async def test_e2e_delete_with_low_confidence():
    """
    End-to-end test for DELETE intent with low evidence confidence.
    
    Tests that the system handles low confidence gracefully with limitation statements.
    """
    
    mock_db = AsyncMock()
    nlq_engine = NLQEngine(db=mock_db)
    
    # Mock intent engine
    mock_intent = MagicMock()
    mock_intent.intent = IntentType.DELETE
    mock_intent.target_type = TargetType.SERVICE
    mock_intent.target_name = "AuthService"
    mock_intent.confidence = 0.95
    mock_intent.requires_llm = False
    mock_intent.reasoning = "Classified as DELETE intent"
    mock_intent.extracted_entities = []
    
    mock_intent_response = MagicMock()
    mock_intent_response.intent = mock_intent
    mock_intent_response.processing_time_ms = 5.0
    
    nlq_engine.intent_engine.classify = Mock(return_value=mock_intent_response)
    
    # Mock entity resolver
    nlq_engine.entity_resolver.resolve = Mock(return_value={
        "node_id": str(uuid4()),
        "name": "AuthService",
        "type": "service"
    })
    
    # Mock repository data collector with low confidence evidence
    nlq_engine.repository_data_collector.collect_repository_data = AsyncMock(return_value={
        'ast_nodes': [],  # Empty AST nodes
        'dependency_graph': DependencyGraph(nodes=[], edges=[], total_nodes=0, total_edges=0),
        'call_graph': CallGraph(function_calls=[], call_depth=0, entry_points=[]),
        'classes': [],
        'functions': [],
        'api_routes': [],
        'imports': []
    })
    
    # Mock impact analysis
    nlq_engine.impact_analysis.analyze_impact = Mock(return_value={
        "summary": "Limited analysis due to low evidence confidence",
        "evidence": {},
        "processing_time_ms": 50.0
    })
    
    # Execute the test
    question = "What breaks if I delete AuthService?"
    repo_id = str(uuid4())
    
    result = await nlq_engine.process_question(
        repo_id=repo_id,
        question=question,
        db=mock_db
    )
    
    # Verify response still completes without exceptions
    assert result["question"] == question
    assert result["intent"] == "DELETE"
    
    # Verify limitation statements are present
    assert len(result["limitations"]) > 0 or result["engineering_evidence"]["evidence_confidence"] < 0.5
    
    # Verify response still has required structure
    assert "engineering_decision" in result
    assert "risk_assessment" in result
    assert "implementation_plan" in result
    
    print("✓ DELETE intent with low confidence end-to-end test passed")
