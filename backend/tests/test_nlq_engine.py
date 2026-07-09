"""
Test suite for Natural Language Question Engine with repository-aware reasoning
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from app.services.nlq_engine import NLQEngine
from app.schemas.nlq import NLQRequest, NLQResponse
from app.services.intent.schemas import IntentType, TargetType
from app.services.engineering_evidence.models import EngineeringEvidence, ASTNode, DependencyGraph, CallGraph


class TestNLQEngine:
    """Test suite for NLQ Engine."""
    
    @pytest.fixture
    def nlq_engine(self):
        """Create a NLQ Engine instance with mocked sub-engines."""
        with patch('app.services.nlq_engine.IntentEngine'), \
             patch('app.services.nlq_engine.EntityResolver'), \
             patch('app.services.nlq_engine.ReferenceIntelligenceEngine'), \
             patch('app.services.nlq_engine.EvidenceEngine'), \
             patch('app.services.nlq_engine.ImpactAnalysisEngine'), \
             patch('app.services.nlq_engine.ReasoningEngine'), \
             patch('app.services.nlq_engine.SimulationEngine'):
            
            engine = NLQEngine()
            return engine
    
    @pytest.mark.asyncio
    async def test_process_question_delete_intent(self, nlq_engine):
        """Test processing a DELETE intent question."""
        # Mock the intent engine response
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
        
        nlq_engine.intent_engine.classify.return_value = mock_intent_response
        
        # Mock entity resolver
        nlq_engine.entity_resolver.resolve.return_value = {
            "node_id": "node-123",
            "name": "AuthService",
            "type": "service"
        }
        
        # Mock repository data collector
        nlq_engine.repository_data_collector.collect_repository_data = AsyncMock(return_value={
            'ast_nodes': [],
            'dependency_graph': DependencyGraph(nodes=[], edges=[], total_nodes=0, total_edges=0),
            'call_graph': CallGraph(function_calls=[], call_depth=0, entry_points=[]),
            'classes': [],
            'functions': [],
            'api_routes': [],
            'imports': []
        })
        
        # Mock impact analysis
        nlq_engine.impact_analysis.analyze_impact.return_value = {
            "summary": "Deleting AuthService would break 5 components",
            "evidence": {"affected_components": ["UserService", "PaymentService"]},
            "processing_time_ms": 50.0
        }
        
        result = await nlq_engine.process_question(
            repo_id="test-repo",
            question="What breaks if I delete AuthService?"
        )
        
        assert result["question"] == "What breaks if I delete AuthService?"
        assert result["intent"] == "DELETE"
        assert result["target_name"] == "AuthService"
        assert result["confidence"] == 0.95
        assert "Deleting AuthService" in result["answer"]
        assert result["processing_time_ms"] > 0
        assert "grounded_in_repository" in result
    
    @pytest.mark.asyncio
    async def test_process_question_rename_intent(self, nlq_engine):
        """Test processing a RENAME intent question."""
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
        
        nlq_engine.intent_engine.classify.return_value = mock_intent_response
        
        nlq_engine.entity_resolver.resolve.return_value = {
            "node_id": "node-456",
            "name": "UserService",
            "type": "service"
        }
        
        nlq_engine.repository_data_collector.collect_repository_data = AsyncMock(return_value={
            'ast_nodes': [],
            'dependency_graph': DependencyGraph(nodes=[], edges=[], total_nodes=0, total_edges=0),
            'call_graph': CallGraph(function_calls=[], call_depth=0, entry_points=[]),
            'classes': [],
            'functions': [],
            'api_routes': [],
            'imports': []
        })
        
        nlq_engine.reference_intelligence.find_references.return_value = [
            {"file": "auth.py", "line": 10},
            {"file": "payment.py", "line": 25}
        ]
        
        result = await nlq_engine.process_question(
            repo_id="test-repo",
            question="Rename UserService to CustomerService"
        )
        
        assert result["intent"] == "RENAME"
        assert result["target_name"] == "UserService"
        assert "references" in result["answer"].lower()
    
    def test_process_question_dependency_query(self, nlq_engine):
        """Test processing a DEPENDENCY_QUERY intent question."""
        mock_intent = MagicMock()
        mock_intent.intent = IntentType.DEPENDENCY_QUERY
        mock_intent.target_type = TargetType.SERVICE
        mock_intent.target_name = "PaymentService"
        mock_intent.confidence = 0.88
        mock_intent.requires_llm = False
        mock_intent.reasoning = "Classified as DEPENDENCY_QUERY intent"
        mock_intent.extracted_entities = []
        
        mock_intent_response = MagicMock()
        mock_intent_response.intent = mock_intent
        mock_intent_response.processing_time_ms = 4.0
        
        nlq_engine.intent_engine.classify.return_value = mock_intent_response
        
        nlq_engine.entity_resolver.resolve.return_value = {
            "node_id": "node-789",
            "name": "PaymentService",
            "type": "service"
        }
        
        nlq_engine.evidence_engine.analyze_dependencies.return_value = {
            "upstream": ["DatabaseService", "AuthService"],
            "downstream": ["OrderService", "InvoiceService"]
        }
        
        result = nlq_engine.process_question(
            repo_id="test-repo",
            question="What does PaymentService depend on?"
        )
        
        assert result["intent"] == "DEPENDENCY_QUERY"
        assert result["target_name"] == "PaymentService"
        assert "depend" in result["answer"].lower()
    
    def test_process_question_repository_query(self, nlq_engine):
        """Test processing a REPOSITORY_QUERY intent question."""
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
        
        nlq_engine.intent_engine.classify.return_value = mock_intent_response
        
        nlq_engine.evidence_engine.get_repository_overview.return_value = {
            "total_files": 150,
            "total_services": 12,
            "total_classes": 45
        }
        
        result = nlq_engine.process_question(
            repo_id="test-repo",
            question="What services are in the repository?"
        )
        
        assert result["intent"] == "REPOSITORY_QUERY"
        assert "150" in result["answer"]
        assert "12" in result["answer"]
    
    def test_process_question_architecture_guidance(self, nlq_engine):
        """Test processing an ARCHITECTURE_GUIDANCE intent question."""
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
        
        nlq_engine.intent_engine.classify.return_value = mock_intent_response
        
        nlq_engine.reference_intelligence.analyze_architecture.return_value = {
            "summary": "Payment module structure",
            "components": ["PaymentService", "PaymentController"]
        }
        
        nlq_engine.reasoning_engine.provide_architecture_guidance.return_value = {
            "recommendation": "Consider separating concerns into distinct layers"
        }
        
        result = nlq_engine.process_question(
            repo_id="test-repo",
            question="How should I structure the payment module?"
        )
        
        assert result["intent"] == "ARCHITECTURE_GUIDANCE"
        assert result["target_name"] == "payment module"
    
    def test_process_question_feature_planning(self, nlq_engine):
        """Test processing a FEATURE_PLANNING intent question."""
        mock_intent = MagicMock()
        mock_intent.intent = IntentType.FEATURE_PLANNING
        mock_intent.target_type = TargetType.UNKNOWN
        mock_intent.target_name = "notification system"
        mock_intent.confidence = 0.82
        mock_intent.requires_llm = False
        mock_intent.reasoning = "Classified as FEATURE_PLANNING intent"
        mock_intent.extracted_entities = []
        
        mock_intent_response = MagicMock()
        mock_intent_response.intent = mock_intent
        mock_intent_response.processing_time_ms = 7.0
        
        nlq_engine.intent_engine.classify.return_value = mock_intent_response
        
        nlq_engine.reasoning_engine.plan_feature.return_value = {
            "summary": "Implement notification service with email and SMS support",
            "steps": ["Create NotificationService", "Add templates", "Integrate with providers"]
        }
        
        result = nlq_engine.process_question(
            repo_id="test-repo",
            question="How do I implement a new notification system?"
        )
        
        assert result["intent"] == "FEATURE_PLANNING"
        assert "notification system" in result["target_name"]
    
    def test_process_question_refactoring_guidance(self, nlq_engine):
        """Test processing a REFACTORING_GUIDANCE intent question."""
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
        
        nlq_engine.intent_engine.classify.return_value = mock_intent_response
        
        nlq_engine.reference_intelligence.analyze_code.return_value = {
            "summary": "OrderService has high complexity",
            "metrics": {"cyclomatic_complexity": 15}
        }
        
        nlq_engine.simulation_engine.simulate_refactoring.return_value = {
            "recommendation": "Extract validation logic into separate validator"
        }
        
        result = nlq_engine.process_question(
            repo_id="test-repo",
            question="How should I refactor the OrderService?"
        )
        
        assert result["intent"] == "REFACTORING_GUIDANCE"
        assert result["target_name"] == "OrderService"
    
    def test_process_question_explain_intent(self, nlq_engine):
        """Test processing an EXPLAIN intent question."""
        mock_intent = MagicMock()
        mock_intent.intent = IntentType.EXPLAIN
        mock_intent.target_type = TargetType.CLASS
        mock_intent.target_name = "User"
        mock_intent.confidence = 0.92
        mock_intent.requires_llm = False
        mock_intent.reasoning = "Classified as EXPLAIN intent"
        mock_intent.extracted_entities = []
        
        mock_intent_response = MagicMock()
        mock_intent_response.intent = mock_intent
        mock_intent_response.processing_time_ms = 3.5
        
        nlq_engine.intent_engine.classify.return_value = mock_intent_response
        
        nlq_engine.reference_intelligence.explain.return_value = {
            "explanation": "User class represents application users with authentication"
        }
        
        result = nlq_engine.process_question(
            repo_id="test-repo",
            question="Explain the User class"
        )
        
        assert result["intent"] == "EXPLAIN"
        assert result["target_name"] == "User"
        assert "User class" in result["answer"]
    
    def test_process_question_move_intent(self, nlq_engine):
        """Test processing a MOVE intent question."""
        mock_intent = MagicMock()
        mock_intent.intent = IntentType.MOVE
        mock_intent.target_type = TargetType.SERVICE
        mock_intent.target_name = "AuthService"
        mock_intent.confidence = 0.91
        mock_intent.requires_llm = False
        mock_intent.reasoning = "Classified as MOVE intent"
        mock_intent.extracted_entities = []
        
        mock_intent_response = MagicMock()
        mock_intent_response.intent = mock_intent
        mock_intent_response.processing_time_ms = 4.5
        
        nlq_engine.intent_engine.classify.return_value = mock_intent_response
        
        nlq_engine.entity_resolver.resolve.return_value = {
            "node_id": "node-123",
            "name": "AuthService",
            "type": "service"
        }
        
        nlq_engine.impact_analysis.analyze_impact.return_value = {
            "summary": "Moving AuthService would require updating 3 import statements",
            "evidence": {"affected_files": ["main.py", "app.py"]},
            "processing_time_ms": 45.0
        }
        
        result = nlq_engine.process_question(
            repo_id="test-repo",
            question="Move AuthService to the auth module"
        )
        
        assert result["intent"] == "MOVE"
        assert result["target_name"] == "AuthService"
        assert "Moving" in result["answer"]
    
    def test_process_question_modify_intent(self, nlq_engine):
        """Test processing a MODIFY intent question."""
        mock_intent = MagicMock()
        mock_intent.intent = IntentType.MODIFY
        mock_intent.target_type = TargetType.SERVICE
        mock_intent.target_name = "PaymentService"
        mock_intent.confidence = 0.93
        mock_intent.requires_llm = False
        mock_intent.reasoning = "Classified as MODIFY intent"
        mock_intent.extracted_entities = []
        
        mock_intent_response = MagicMock()
        mock_intent_response.intent = mock_intent
        mock_intent_response.processing_time_ms = 5.5
        
        nlq_engine.intent_engine.classify.return_value = mock_intent_response
        
        nlq_engine.entity_resolver.resolve.return_value = {
            "node_id": "node-789",
            "name": "PaymentService",
            "type": "service"
        }
        
        nlq_engine.impact_analysis.analyze_impact.return_value = {
            "summary": "Modifying PaymentService could affect checkout flow",
            "evidence": {"affected_workflows": ["checkout", "subscription"]},
            "processing_time_ms": 55.0
        }
        
        result = nlq_engine.process_question(
            repo_id="test-repo",
            question="Modify the PaymentService"
        )
        
        assert result["intent"] == "MODIFY"
        assert result["target_name"] == "PaymentService"
        assert "Modifying" in result["answer"]
    
    def test_resolve_entities_with_primary_target(self, nlq_engine):
        """Test entity resolution with primary target."""
        mock_intent = MagicMock()
        mock_intent.target_name = "AuthService"
        mock_intent.target_type = TargetType.SERVICE
        mock_intent.extracted_entities = []
        
        nlq_engine.entity_resolver.resolve.return_value = {
            "node_id": "node-123",
            "name": "AuthService",
            "type": "service"
        }
        
        result = nlq_engine._resolve_entities(repo_id="test-repo", intent=mock_intent)
        
        assert result["primary_target"] is not None
        assert result["primary_target"]["name"] == "AuthService"
        nlq_engine.entity_resolver.resolve.assert_called_once()
    
    def test_resolve_entities_with_related_entities(self, nlq_engine):
        """Test entity resolution with related entities."""
        mock_entity = MagicMock()
        mock_entity.name = "UserService"
        mock_entity.type = TargetType.SERVICE
        
        mock_intent = MagicMock()
        mock_intent.target_name = "AuthService"
        mock_intent.target_type = TargetType.SERVICE
        mock_intent.extracted_entities = [mock_entity]
        
        nlq_engine.entity_resolver.resolve.return_value = {
            "node_id": "node-456",
            "name": "UserService",
            "type": "service"
        }
        
        result = nlq_engine._resolve_entities(repo_id="test-repo", intent=mock_intent)
        
        assert len(result["related_entities"]) == 1
        assert result["related_entities"][0]["name"] == "UserService"
    
    def test_handle_general_intent(self, nlq_engine):
        """Test handling of GENERAL/UNKNOWN intents."""
        mock_intent = MagicMock()
        mock_intent.intent = IntentType.UNKNOWN
        mock_intent.target_name = "something"
        mock_intent.target_type = TargetType.UNKNOWN
        
        mock_evidence = MagicMock()
        mock_evidence.evidence_confidence = 0.8
        
        result = nlq_engine._handle_general_intent(
            repo_id="test-repo",
            intent=mock_intent,
            resolved_entities={},
            engineering_evidence=mock_evidence
        )
        
        assert "not sure how to help" in result["answer"]
        assert result["evidence"] is None
    
    @pytest.mark.asyncio
    async def test_collect_engineering_evidence(self, nlq_engine):
        """Test collection of engineering evidence."""
        mock_intent = MagicMock()
        mock_intent.target_name = "AuthService"
        mock_intent.target_type = TargetType.SERVICE
        
        # Mock repository data collector
        nlq_engine.repository_data_collector.collect_repository_data = AsyncMock(return_value={
            'ast_nodes': [ASTNode(node_type="class", name="AuthService", file_path="auth.py", line_number=10)],
            'dependency_graph': DependencyGraph(nodes=["AuthService"], edges=[], total_nodes=1, total_edges=0),
            'call_graph': CallGraph(function_calls=[], call_depth=0, entry_points=[]),
            'classes': [],
            'functions': [],
            'api_routes': [],
            'imports': []
        })
        
        evidence = await nlq_engine._collect_engineering_evidence(
            repo_id="test-repo",
            intent=mock_intent,
            resolved_entities={},
            db=None
        )
        
        assert evidence.target_name == "AuthService"
        assert len(evidence.ast_nodes) == 1
        assert evidence.evidence_confidence >= 0.0
    
    def test_validate_evidence_high_confidence(self, nlq_engine):
        """Test evidence validation with high confidence."""
        mock_evidence = MagicMock()
        mock_evidence.evidence_confidence = 0.9
        mock_evidence.data_completeness = {
            'ast_nodes': 0.8,
            'functions': 0.9,
            'imports': 0.7
        }
        mock_evidence.limitations = []
        
        result = nlq_engine._validate_evidence(mock_evidence)
        
        assert result["is_valid"] is True
        assert result["has_limitations"] is False
        assert len(result["errors"]) == 0
    
    def test_validate_evidence_low_confidence(self, nlq_engine):
        """Test evidence validation with low confidence."""
        mock_evidence = MagicMock()
        mock_evidence.evidence_confidence = 0.2
        mock_evidence.data_completeness = {
            'ast_nodes': 0.1,
            'functions': 0.1,
            'imports': 0.1
        }
        mock_evidence.limitations = ["Limited AST information"]
        
        result = nlq_engine._validate_evidence(mock_evidence)
        
        assert result["is_valid"] is False
        assert result["has_limitations"] is True
        assert len(result["errors"]) > 0
    
    def test_add_limitation_context(self, nlq_engine):
        """Test adding limitation context to answers."""
        answer = "This is the original answer."
        limitations = ["Limited AST information", "Low confidence"]
        
        result = nlq_engine._add_limitation_context(answer, limitations)
        
        assert "This is the original answer." in result
        assert "**Limitations:**" in result
        assert "Limited AST information" in result
        assert "Low confidence" in result
    
    def test_add_limitation_context_no_limitations(self, nlq_engine):
        """Test adding limitation context when there are no limitations."""
        answer = "This is the original answer."
        limitations = []
        
        result = nlq_engine._add_limitation_context(answer, limitations)
        
        assert result == answer
        assert "**Limitations:**" not in result


class TestNLQRequest:
    """Test suite for NLQ request schema."""
    
    def test_nlq_request_valid(self):
        """Test valid NLQ request."""
        request = NLQRequest(
            repo_id="test-repo-id",
            question="What breaks if I delete AuthService?"
        )
        
        assert request.repo_id == "test-repo-id"
        assert request.question == "What breaks if I delete AuthService?"
    
    def test_nlq_request_missing_fields(self):
        """Test NLQ request with missing fields."""
        with pytest.raises(ValueError):
            NLQRequest(repo_id="test-repo-id")
        
        with pytest.raises(ValueError):
            NLQRequest(question="What breaks?")


class TestNLQResponse:
    """Test suite for NLQ response schema."""
    
    def test_nlq_response_valid(self):
        """Test valid NLQ response."""
        response = NLQResponse(
            question="What breaks if I delete AuthService?",
            intent="DELETE",
            target_type="service",
            target_name="AuthService",
            confidence=0.95,
            reasoning="Classified as DELETE intent",
            extracted_entities=[],
            resolved_entities={},
            answer="Deleting AuthService would break 5 components",
            evidence={"affected": ["UserService"]},
            processing_time_ms=55.0,
            requires_llm=False
        )
        
        assert response.question == "What breaks if I delete AuthService?"
        assert response.intent == "DELETE"
        assert response.confidence == 0.95
        assert response.requires_llm is False
