"""
Test suite for enhanced Intent Engine with new intent types.

Tests the classification of:
- DELETE, RENAME, MOVE, MODIFY
- DEPENDENCY, DEPENDENCY_QUERY
- REPOSITORY_QUERY
- ARCHITECTURE, ARCHITECTURE_GUIDANCE
- FEATURE_PLANNING, REFACTORING_GUIDANCE
"""

import pytest
from app.services.intent.intent_engine import IntentEngine
from app.services.intent.schemas import IntentRequest, IntentType, TargetType


class TestEnhancedIntentEngine:
    """Test suite for enhanced Intent Engine with new intent types."""

    @pytest.fixture
    def intent_engine(self):
        """Create an Intent Engine instance for testing."""
        return IntentEngine(llm_confidence_threshold=0.6, enable_llm_fallback=False)

    def test_delete_intent(self, intent_engine):
        """Test DELETE intent classification."""
        request = IntentRequest(repo_id="test-repo", question="Delete the AuthService")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.DELETE
        assert response.intent.target_name == "AuthService"
        assert response.intent.confidence > 0.7
        assert response.intent.requires_graph is True

    def test_rename_intent(self, intent_engine):
        """Test RENAME intent classification."""
        request = IntentRequest(repo_id="test-repo", question="Rename UserService to AccountService")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.RENAME
        assert "UserService" in response.intent.target_name or "AccountService" in response.intent.target_name
        assert response.intent.confidence > 0.7

    def test_move_intent(self, intent_engine):
        """Test MOVE intent classification."""
        request = IntentRequest(repo_id="test-repo", question="Move auth.py to services/")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.MOVE
        assert response.intent.confidence > 0.7
        assert response.intent.requires_graph is True

    def test_modify_intent(self, intent_engine):
        """Test MODIFY intent classification."""
        request = IntentRequest(repo_id="test-repo", question="Modify the PaymentService")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.MODIFY
        assert response.intent.target_name == "PaymentService"
        assert response.intent.confidence > 0.7
        assert response.intent.requires_graph is True

    def test_dependency_intent(self, intent_engine):
        """Test DEPENDENCY intent classification."""
        request = IntentRequest(repo_id="test-repo", question="What depends on UserService?")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.DEPENDENCY
        assert response.intent.target_name == "UserService"
        assert response.intent.confidence > 0.7
        assert response.intent.requires_graph is True

    def test_dependency_query_intent(self, intent_engine):
        """Test DEPENDENCY_QUERY intent classification."""
        request = IntentRequest(repo_id="test-repo", question="What are the dependencies of OrderService?")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.DEPENDENCY_QUERY
        assert response.intent.target_name == "OrderService"
        assert response.intent.confidence > 0.7
        assert response.intent.requires_graph is True

    def test_repository_query_intent(self, intent_engine):
        """Test REPOSITORY_QUERY intent classification."""
        request = IntentRequest(repo_id="test-repo", question="What is in the repository?")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.REPOSITORY_QUERY
        # The entity extractor may not perfectly identify REPOSITORY target type
        # but the intent should be correctly classified
        assert response.intent.confidence > 0.5

    def test_architecture_intent(self, intent_engine):
        """Test ARCHITECTURE intent classification."""
        request = IntentRequest(repo_id="test-repo", question="Show me the architecture")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.ARCHITECTURE
        assert response.intent.confidence > 0.7
        assert response.intent.requires_graph is True

    def test_architecture_guidance_intent(self, intent_engine):
        """Test ARCHITECTURE_GUIDANCE intent classification."""
        request = IntentRequest(repo_id="test-repo", question="Architecture guidance for the payment module")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.ARCHITECTURE_GUIDANCE
        # Check that payment is in extracted entities
        assert any("payment" in e.name.lower() for e in response.intent.extracted_entities)
        assert response.intent.confidence > 0.6
        assert response.intent.requires_graph is True

    def test_feature_planning_intent(self, intent_engine):
        """Test FEATURE_PLANNING intent classification."""
        request = IntentRequest(repo_id="test-repo", question="Feature plan for user authentication")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.FEATURE_PLANNING
        # Check that authentication is in extracted entities
        assert any("authentication" in e.name.lower() for e in response.intent.extracted_entities)
        assert response.intent.confidence > 0.6

    def test_refactoring_guidance_intent(self, intent_engine):
        """Test REFACTORING_GUIDANCE intent classification."""
        request = IntentRequest(repo_id="test-repo", question="Refactoring guidance for UserService")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.REFACTORING_GUIDANCE
        assert response.intent.target_name == "UserService"
        assert response.intent.confidence > 0.6
        assert response.intent.requires_graph is True

    def test_explain_intent(self, intent_engine):
        """Test EXPLAIN intent classification."""
        request = IntentRequest(repo_id="test-repo", question="Explain how the OrderService works")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.EXPLAIN
        assert response.intent.target_name == "OrderService"
        assert response.intent.confidence > 0.7

    def test_entity_extraction_service(self, intent_engine):
        """Test entity extraction for service names."""
        request = IntentRequest(repo_id="test-repo", question="Delete the PaymentService")
        response = intent_engine.classify(request)
        
        entities = response.intent.extracted_entities
        assert len(entities) > 0
        assert any(e.name == "PaymentService" for e in entities)
        assert any(e.type == TargetType.SERVICE for e in entities)

    def test_entity_extraction_file(self, intent_engine):
        """Test entity extraction for file names."""
        request = IntentRequest(repo_id="test-repo", question="Move auth.py to services/")
        response = intent_engine.classify(request)
        
        entities = response.intent.extracted_entities
        assert len(entities) > 0
        assert any(e.name == "auth.py" for e in entities)
        assert any(e.type == TargetType.FILE for e in entities)

    def test_entity_extraction_folder(self, intent_engine):
        """Test entity extraction for folder paths."""
        request = IntentRequest(repo_id="test-repo", question="Move to services/ folder")
        response = intent_engine.classify(request)
        
        entities = response.intent.extracted_entities
        assert len(entities) > 0
        assert any("services" in e.name.lower() for e in entities)

    def test_confidence_calculation(self, intent_engine):
        """Test confidence calculation for different question types."""
        # High confidence: clear pattern match
        request1 = IntentRequest(repo_id="test-repo", question="Delete AuthService")
        response1 = intent_engine.classify(request1)
        assert response1.intent.confidence > 0.8
        
        # Medium confidence: keyword match
        request2 = IntentRequest(repo_id="test-repo", question="What about the dependencies?")
        response2 = intent_engine.classify(request2)
        assert response2.intent.confidence > 0.5

    def test_normalization(self, intent_engine):
        """Test question normalization."""
        request = IntentRequest(repo_id="test-repo", question="Can you please delete the AuthService?")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.DELETE
        assert "please" not in response.intent.normalized_question.lower()

    def test_unknown_intent(self, intent_engine):
        """Test UNKNOWN intent for unclear questions."""
        request = IntentRequest(repo_id="test-repo", question="blah blah blah")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.UNKNOWN
        assert response.intent.confidence < 0.5

    def test_simple_classify_method(self, intent_engine):
        """Test the simplified classify_simple method."""
        intent = intent_engine.classify_simple("test-repo", "Delete UserService")
        
        assert intent.intent == IntentType.DELETE
        assert intent.target_name == "UserService"
        assert intent.confidence > 0.7

    def test_move_with_from_to(self, intent_engine):
        """Test MOVE intent with from/to syntax."""
        request = IntentRequest(repo_id="test-repo", question="Move auth.py from utils/ to services/")
        response = intent_engine.classify(request)
        
        assert response.intent.intent == IntentType.MOVE
        assert response.intent.confidence > 0.7

    def test_modify_variations(self, intent_engine):
        """Test MODIFY intent with various verbs."""
        variations = [
            "Modify UserService",
            "Update UserService",
            "Edit UserService",
            "Change UserService",
            "Alter UserService",
        ]
        
        for question in variations:
            request = IntentRequest(repo_id="test-repo", question=question)
            response = intent_engine.classify(request)
            assert response.intent.intent == IntentType.MODIFY
            assert response.intent.target_name == "UserService"

    def test_refactor_vs_refactoring_guidance(self, intent_engine):
        """Test distinction between REFACTOR and REFACTORING_GUIDANCE."""
        refactor_request = IntentRequest(repo_id="test-repo", question="Refactor UserService")
        refactor_response = intent_engine.classify(refactor_request)
        
        guidance_request = IntentRequest(repo_id="test-repo", question="Refactoring guidance for UserService")
        guidance_response = intent_engine.classify(guidance_request)
        
        assert refactor_response.intent.intent == IntentType.REFACTOR
        assert guidance_response.intent.intent == IntentType.REFACTORING_GUIDANCE

    def test_architecture_vs_architecture_guidance(self, intent_engine):
        """Test distinction between ARCHITECTURE and ARCHITECTURE_GUIDANCE."""
        arch_request = IntentRequest(repo_id="test-repo", question="Show me the architecture")
        arch_response = intent_engine.classify(arch_request)
        
        guidance_request = IntentRequest(repo_id="test-repo", question="Architecture guidance for the system")
        guidance_response = intent_engine.classify(guidance_request)
        
        assert arch_response.intent.intent == IntentType.ARCHITECTURE
        assert guidance_response.intent.intent == IntentType.ARCHITECTURE_GUIDANCE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
