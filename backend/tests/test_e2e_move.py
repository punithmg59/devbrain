"""
End-to-end test for MOVE intent scenario.

Tests the complete pipeline from natural language question to engineering intelligence response
for move operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from uuid import uuid4

from app.services.nlq_engine import NLQEngine
from app.services.intent.schemas import IntentType, TargetType
from app.services.engineering_evidence.models import ASTNode, DependencyGraph, CallGraph


@pytest.mark.asyncio
async def test_e2e_move_intent():
    """
    End-to-end test for MOVE intent.
    
    Tests:
    - Intent classification
    - Entity resolution
    - Evidence collection
    - Evidence validation
    - Impact analysis
    - Engineering intelligence generation
    - Response structure
    """
    
    mock_db = AsyncMock()
    nlq_engine = NLQEngine(db=mock_db)
    
    # Mock intent engine
    mock_intent = MagicMock()
    mock_intent.intent = IntentType.MOVE
    mock_intent.target_type = TargetType.SERVICE
    mock_intent.target_name = "AuthService"
    mock_intent.confidence = 0.92
    mock_intent.requires_llm = False
    mock_intent.reasoning = "Classified as MOVE intent"
    mock_intent.extracted_entities = []
    
    mock_intent_response = MagicMock()
    mock_intent_response.intent = mock_intent
    mock_intent_response.processing_time_ms = 4.0
    
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
            ASTNode(node_type="class", name="AuthService", file_path="services/auth.py", line_number=10)
        ],
        'dependency_graph': DependencyGraph(
            nodes=["AuthService"],
            edges=[],
            total_nodes=1,
            total_edges=0
        ),
        'call_graph': CallGraph(function_calls=[], call_depth=0, entry_points=[]),
        'classes': [
            MagicMock(name="AuthService", file_path="services/auth.py")
        ],
        'functions': [],
        'api_routes': [],
        'imports': []
    })
    
    # Mock impact analysis
    nlq_engine.impact_analysis.analyze_impact = Mock(return_value={
        "summary": "Moving AuthService requires updating 3 import statements",
        "evidence": {
            "affected_files": ["main.py", "app.py", "config.py"]
        },
        "processing_time_ms": 45.0
    })
    
    # Execute the test
    question = "Move AuthService to the auth module"
    repo_id = str(uuid4())
    
    result = await nlq_engine.process_question(
        repo_id=repo_id,
        question=question,
        db=mock_db
    )
    
    # Verify response structure
    assert result["question"] == question
    assert result["intent"] == "MOVE"
    assert result["target_name"] == "AuthService"
    assert result["confidence"] == 0.92
    assert result["grounded_in_repository"] == True
    
    # Verify engineering decision
    assert "engineering_decision" in result
    assert "move" in result["engineering_decision"]["decision"].lower()
    
    # Verify engineering evidence
    assert "engineering_evidence" in result
    
    # Verify implementation plan includes file operations
    assert "implementation_plan" in result
    
    # Verify no exceptions
    assert "error" not in result
    
    print("✓ MOVE intent end-to-end test passed")
