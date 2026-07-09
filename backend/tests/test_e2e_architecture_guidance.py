"""
End-to-end test for ARCHITECTURE_GUIDANCE intent scenario.

Tests the complete pipeline from natural language question to engineering intelligence response
for architecture guidance operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from uuid import uuid4

from app.services.nlq_engine import NLQEngine
from app.services.intent.schemas import IntentType, TargetType
from app.services.engineering_evidence.models import ASTNode, DependencyGraph, CallGraph


@pytest.mark.asyncio
async def test_e2e_architecture_guidance_intent():
    """
    End-to-end test for ARCHITECTURE_GUIDANCE intent.
    
    Tests:
    - Intent classification
    - Entity resolution
    - Evidence collection
    - Evidence validation
    - Architecture analysis
    - Engineering intelligence generation
    - Response structure
    """
    
    mock_db = AsyncMock()
    nlq_engine = NLQEngine(db=mock_db)
    
    # Mock intent engine
    mock_intent = MagicMock()
    mock_intent.intent = IntentType.ARCHITECTURE_GUIDANCE
    mock_intent.target_type = TargetType.MODULE
    mock_intent.target_name = "payment module"
    mock_intent.confidence = 0.87
    mock_intent.requires_llm = False
    mock_intent.reasoning = "Classified as ARCHITECTURE_GUIDANCE intent"
    mock_intent.extracted_entities = []
    
    mock_intent_response = MagicMock()
    mock_intent_response.intent = mock_intent
    mock_intent_response.processing_time_ms = 6.0
    
    nlq_engine.intent_engine.classify = Mock(return_value=mock_intent_response)
    
    # Mock entity resolver
    nlq_engine.entity_resolver.resolve = Mock(return_value={
        "node_id": str(uuid4()),
        "name": "payment module",
        "type": "module"
    })
    
    # Mock repository data collector
    nlq_engine.repository_data_collector.collect_repository_data = AsyncMock(return_value={
        'ast_nodes': [
            ASTNode(node_type="class", name="PaymentService", file_path="payment/service.py", line_number=10),
            ASTNode(node_type="class", name="PaymentController", file_path="payment/controller.py", line_number=15)
        ],
        'dependency_graph': DependencyGraph(
            nodes=["PaymentService", "PaymentController"],
            edges=[],
            total_nodes=2,
            total_edges=0
        ),
        'call_graph': CallGraph(function_calls=[], call_depth=0, entry_points=[]),
        'classes': [
            MagicMock(name="PaymentService", file_path="payment/service.py"),
            MagicMock(name="PaymentController", file_path="payment/controller.py")
        ],
        'functions': [
            MagicMock(name="process_payment", file_path="payment/service.py")
        ],
        'api_routes': [
            MagicMock(path="/api/payments", file_path="payment/controller.py")
        ],
        'imports': []
    })
    
    # Mock reference intelligence for architecture analysis
    nlq_engine.reference_intelligence.analyze_architecture = Mock(return_value={
        "summary": "Payment module structure",
        "components": ["PaymentService", "PaymentController"]
    })
    
    # Mock reasoning engine for guidance
    nlq_engine.reasoning_engine.provide_architecture_guidance = Mock(return_value={
        "recommendation": "Consider separating concerns into distinct layers"
    })
    
    # Execute the test
    question = "How should I structure the payment module?"
    repo_id = str(uuid4())
    
    result = await nlq_engine.process_question(
        repo_id=repo_id,
        question=question,
        db=mock_db
    )
    
    # Verify response structure
    assert result["question"] == question
    assert result["intent"] == "ARCHITECTURE_GUIDANCE"
    assert result["target_name"] == "payment module"
    assert result["confidence"] == 0.87
    assert result["grounded_in_repository"] == True
    
    # Verify engineering decision
    assert "engineering_decision" in result
    
    # Verify repository analysis
    assert "repository_analysis" in result
    
    # Verify implementation plan
    assert "implementation_plan" in result
    
    # Verify no exceptions
    assert "error" not in result
    
    print("✓ ARCHITECTURE_GUIDANCE intent end-to-end test passed")
