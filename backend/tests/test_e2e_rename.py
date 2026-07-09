"""
End-to-end test for RENAME intent scenario.

Tests the complete pipeline from natural language question to engineering intelligence response
for rename operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from uuid import uuid4

from app.services.nlq_engine import NLQEngine
from app.services.intent.schemas import IntentType, TargetType
from app.services.engineering_evidence.models import ASTNode, DependencyGraph, CallGraph


@pytest.mark.asyncio
async def test_e2e_rename_intent():
    """
    End-to-end test for RENAME intent.
    
    Tests:
    - Intent classification
    - Entity resolution
    - Evidence collection
    - Evidence validation
    - Reference finding
    - Engineering intelligence generation
    - Response structure
    """
    
    mock_db = AsyncMock()
    nlq_engine = NLQEngine(db=mock_db)
    
    # Mock intent engine
    mock_intent = MagicMock()
    mock_intent.intent = IntentType.RENAME
    mock_intent.target_type = TargetType.SERVICE
    mock_intent.target_name = "UserService"
    mock_intent.confidence = 0.90
    mock_intent.requires_llm = False
    mock_intent.reasoning = "Classified as RENAME intent"
    mock_intent.extracted_entities = []
    
    mock_intent_response = MagicMock()
    mock_intent_response.intent = mock_intent
    mock_intent_response.processing_time_ms = 3.0
    
    nlq_engine.intent_engine.classify = Mock(return_value=mock_intent_response)
    
    # Mock entity resolver
    nlq_engine.entity_resolver.resolve = Mock(return_value={
        "node_id": str(uuid4()),
        "name": "UserService",
        "type": "service"
    })
    
    # Mock repository data collector
    nlq_engine.repository_data_collector.collect_repository_data = AsyncMock(return_value={
        'ast_nodes': [
            ASTNode(node_type="class", name="UserService", file_path="user.py", line_number=10)
        ],
        'dependency_graph': DependencyGraph(
            nodes=["UserService", "AuthService"],
            edges=[],
            total_nodes=2,
            total_edges=0
        ),
        'call_graph': CallGraph(function_calls=[], call_depth=0, entry_points=[]),
        'classes': [
            MagicMock(name="UserService", file_path="user.py")
        ],
        'functions': [
            MagicMock(name="create_user", file_path="user.py"),
            MagicMock(name="update_user", file_path="user.py")
        ],
        'api_routes': [
            MagicMock(path="/api/users", file_path="user.py")
        ],
        'imports': [
            MagicMock(module="pydantic", file_path="user.py")
        ]
    })
    
    # Mock reference intelligence
    nlq_engine.reference_intelligence.find_references = Mock(return_value=[
        {"file": "auth.py", "line": 10},
        {"file": "payment.py", "line": 25},
        {"file": "order.py", "line": 40}
    ])
    
    # Execute the test
    question = "Rename UserService to CustomerService"
    repo_id = str(uuid4())
    
    result = await nlq_engine.process_question(
        repo_id=repo_id,
        question=question,
        db=mock_db
    )
    
    # Verify response structure
    assert result["question"] == question
    assert result["intent"] == "RENAME"
    assert result["target_name"] == "UserService"
    assert result["confidence"] == 0.90
    assert result["grounded_in_repository"] == True
    
    # Verify engineering decision
    assert "engineering_decision" in result
    assert "rename" in result["engineering_decision"]["decision"].lower()
    
    # Verify engineering evidence
    assert "engineering_evidence" in result
    assert result["engineering_evidence"]["evidence_confidence"] > 0
    
    # Verify affected components
    assert "affected_components" in result
    assert len(result["affected_components"]) > 0
    
    # Verify implementation plan includes reference updates
    assert "implementation_plan" in result
    assert len(result["implementation_plan"]["steps"]) > 0
    
    # Verify no exceptions
    assert "error" not in result
    
    print("✓ RENAME intent end-to-end test passed")
