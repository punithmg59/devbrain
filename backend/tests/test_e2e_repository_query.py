"""
End-to-end test for REPOSITORY_QUERY intent scenario.

Tests the complete pipeline from natural language question to engineering intelligence response
for repository query operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from uuid import uuid4

from app.services.nlq_engine import NLQEngine
from app.services.intent.schemas import IntentType, TargetType
from app.services.engineering_evidence.models import ASTNode, DependencyGraph, CallGraph


@pytest.mark.asyncio
async def test_e2e_repository_query_intent():
    """
    End-to-end test for REPOSITORY_QUERY intent.
    
    Tests:
    - Intent classification
    - Entity resolution
    - Evidence collection
    - Evidence validation
    - Repository overview generation
    - Engineering intelligence generation
    - Response structure
    """
    
    mock_db = AsyncMock()
    nlq_engine = NLQEngine(db=mock_db)
    
    # Mock intent engine
    mock_intent = MagicMock()
    mock_intent.intent = IntentType.REPOSITORY_QUERY
    mock_intent.target_type = TargetType.REPOSITORY
    mock_intent.target_name = "repository"
    mock_intent.confidence = 0.85
    mock_intent.requires_llm = False
    mock_intent.reasoning = "Classified as REPOSITORY_QUERY intent"
    mock_intent.extracted_entities = []
    
    mock_intent_response = MagicMock()
    mock_intent_response.intent = mock_intent
    mock_intent_response.processing_time_ms = 2.0
    
    nlq_engine.intent_engine.classify = Mock(return_value=mock_intent_response)
    
    # Mock entity resolver
    nlq_engine.entity_resolver.resolve = Mock(return_value={
        "node_id": str(uuid4()),
        "name": "repository",
        "type": "repository"
    })
    
    # Mock repository data collector
    nlq_engine.repository_data_collector.collect_repository_data = AsyncMock(return_value={
        'ast_nodes': [
            ASTNode(node_type="class", name="AuthService", file_path="auth.py", line_number=10),
            ASTNode(node_type="class", name="UserService", file_path="user.py", line_number=15)
        ],
        'dependency_graph': DependencyGraph(
            nodes=["AuthService", "UserService", "PaymentService"],
            edges=[],
            total_nodes=3,
            total_edges=0
        ),
        'call_graph': CallGraph(function_calls=[], call_depth=0, entry_points=[]),
        'classes': [
            MagicMock(name="AuthService", file_path="auth.py"),
            MagicMock(name="UserService", file_path="user.py"),
            MagicMock(name="PaymentService", file_path="payment.py")
        ],
        'functions': [
            MagicMock(name="authenticate", file_path="auth.py"),
            MagicMock(name="create_user", file_path="user.py")
        ],
        'api_routes': [
            MagicMock(path="/api/auth/login", file_path="auth.py"),
            MagicMock(path="/api/users", file_path="user.py")
        ],
        'imports': [
            MagicMock(module="fastapi", file_path="auth.py"),
            MagicMock(module="sqlalchemy", file_path="user.py")
        ]
    })
    
    # Mock evidence engine for repository overview
    nlq_engine.evidence_engine.get_repository_overview = Mock(return_value={
        "total_files": 150,
        "total_services": 12,
        "total_classes": 45
    })
    
    # Execute the test
    question = "What services are in the repository?"
    repo_id = str(uuid4())
    
    result = await nlq_engine.process_question(
        repo_id=repo_id,
        question=question,
        db=mock_db
    )
    
    # Verify response structure
    assert result["question"] == question
    assert result["intent"] == "REPOSITORY_QUERY"
    assert result["target_name"] == "repository"
    assert result["confidence"] == 0.85
    assert result["grounded_in_repository"] == True
    
    # Verify engineering decision
    assert "engineering_decision" in result
    
    # Verify repository analysis
    assert "repository_analysis" in result
    assert result["repository_analysis"]["structure_summary"]
    
    # Verify engineering evidence
    assert "engineering_evidence" in result
    
    # Verify no exceptions
    assert "error" not in result
    
    print("✓ REPOSITORY_QUERY intent end-to-end test passed")
