"""
End-to-end test for REFACTORING_GUIDANCE intent scenario.

Tests the complete pipeline from natural language question to engineering intelligence response
for refactoring guidance operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from uuid import uuid4

from app.services.nlq_engine import NLQEngine
from app.services.intent.schemas import IntentType, TargetType
from app.services.engineering_evidence.models import ASTNode, DependencyGraph, CallGraph


@pytest.mark.asyncio
async def test_e2e_refactoring_guidance_intent():
    """
    End-to-end test for REFACTORING_GUIDANCE intent.
    
    Tests:
    - Intent classification
    - Entity resolution
    - Evidence collection
    - Evidence validation
    - Code analysis
    - Simulation
    - Engineering intelligence generation
    - Response structure
    """
    
    mock_db = AsyncMock()
    nlq_engine = NLQEngine(db=mock_db)
    
    # Mock intent engine
    mock_intent = MagicMock()
    mock_intent.intent = IntentType.REFACTORING_GUIDANCE
    mock_intent.target_type = TargetType.SERVICE
    mock_intent.target_name = "OrderService"
    mock_intent.confidence = 0.89
    mock_intent.requires_llm = False
    mock_intent.reasoning = "Classified as REFACTORING_GUIDANCE intent"
    mock_intent.extracted_entities = []
    
    mock_intent_response = MagicMock()
    mock_intent_response.intent = mock_intent
    mock_intent_response.processing_time_ms = 8.0
    
    nlq_engine.intent_engine.classify = Mock(return_value=mock_intent_response)
    
    # Mock entity resolver
    nlq_engine.entity_resolver.resolve = Mock(return_value={
        "node_id": str(uuid4()),
        "name": "OrderService",
        "type": "service"
    })
    
    # Mock repository data collector
    nlq_engine.repository_data_collector.collect_repository_data = AsyncMock(return_value={
        'ast_nodes': [
            ASTNode(node_type="class", name="OrderService", file_path="order.py", line_number=10)
        ],
        'dependency_graph': DependencyGraph(
            nodes=["OrderService"],
            edges=[],
            total_nodes=1,
            total_edges=0
        ),
        'call_graph': CallGraph(function_calls=[], call_depth=0, entry_points=[]),
        'classes': [
            MagicMock(name="OrderService", file_path="order.py")
        ],
        'functions': [
            MagicMock(name="create_order", file_path="order.py"),
            MagicMock(name="update_order", file_path="order.py"),
            MagicMock(name="delete_order", file_path="order.py"),
            MagicMock(name="get_order", file_path="order.py")
        ],
        'api_routes': [
            MagicMock(path="/api/orders", file_path="order.py")
        ],
        'imports': []
    })
    
    # Mock reference intelligence for code analysis
    nlq_engine.reference_intelligence.analyze_code = Mock(return_value={
        "summary": "OrderService has high complexity",
        "metrics": {"cyclomatic_complexity": 15}
    })
    
    # Mock simulation engine for refactoring simulation
    nlq_engine.simulation_engine.simulate_refactoring = Mock(return_value={
        "recommendation": "Extract validation logic into separate validator"
    })
    
    # Execute the test
    question = "How should I refactor the OrderService?"
    repo_id = str(uuid4())
    
    result = await nlq_engine.process_question(
        repo_id=repo_id,
        question=question,
        db=mock_db
    )
    
    # Verify response structure
    assert result["question"] == question
    assert result["intent"] == "REFACTORING_GUIDANCE"
    assert result["target_name"] == "OrderService"
    assert result["confidence"] == 0.89
    assert result["grounded_in_repository"] == True
    
    # Verify engineering decision
    assert "engineering_decision" in result
    assert "refactor" in result["engineering_decision"]["decision"].lower()
    
    # Verify repository analysis
    assert "repository_analysis" in result
    
    # Verify recommended changes
    assert "recommended_changes" in result
    assert len(result["recommended_changes"]) > 0
    
    # Verify implementation plan
    assert "implementation_plan" in result
    
    # Verify no exceptions
    assert "error" not in result
    
    print("✓ REFACTORING_GUIDANCE intent end-to-end test passed")
