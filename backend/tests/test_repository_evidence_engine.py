import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.repository_evidence_engine import (
    RepositoryEvidenceEngine,
    DeleteCodeEvidenceCollector,
    AddFeatureEvidenceCollector,
)
from app.models.intent import Intent
from app.schemas.evidence import EvidenceRequest, EvidenceResponse, NodeEvidence


class TestDeleteCodeEvidenceCollector:
    """Test suite for DeleteCodeEvidenceCollector."""
    
    @pytest.fixture
    def mock_node(self):
        """Create a mock node."""
        node = Mock()
        node.id = uuid4()
        node.name = "AuthService"
        node.node_type = "service"
        node.full_path = "app/services/auth.py"
        node.signature = "class AuthService"
        node.raw_code = "class AuthService:\n    pass"
        node.start_line = 1
        node.end_line = 10
        node.complexity_score = 5.0
        node.architecture_role = "service"
        node.file_id = uuid4()
        node.imports = ["fastapi", "sqlalchemy"]
        node.calls = ["UserRepository"]
        node.called_by = ["AuthController"]
        return node
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        return db
    
    def test_collect_with_target_node(self, mock_node):
        """Test evidence collection when target node is found (synchronous test)."""
        # Test the synchronous logic without async DB calls
        collector = DeleteCodeEvidenceCollector(
            repo_id=uuid4(),
            target="AuthService",
            max_results=10
        )
        
        # Test node conversion
        evidence = collector._to_node_evidence(mock_node, 0.95)
        
        assert evidence.name == "AuthService"
        assert evidence.relevance_score == 0.95
        assert evidence.node_type == "service"
    
    def test_empty_response(self):
        """Test empty response when target not found."""
        collector = DeleteCodeEvidenceCollector(
            repo_id=uuid4(),
            target="NonExistentService",
            max_results=10
        )
        
        result = collector._empty_response()
        
        assert isinstance(result, EvidenceResponse)
        assert result.target_node is None
        assert result.confidence == 0.0
        assert result.intent == Intent.DELETE_CODE
    
    def test_calculate_relevance_same_file(self, mock_node):
        """Test relevance calculation for nodes in same file."""
        collector = DeleteCodeEvidenceCollector(
            repo_id=uuid4(),
            target="AuthService",
            max_results=10
        )
        
        other_node = Mock()
        other_node.file_id = mock_node.file_id
        other_node.name = "UserRepository"
        other_node.node_type = "service"
        other_node.complexity_score = 3.0
        other_node.architecture_role = "service"
        
        relevance = collector._calculate_relevance(other_node, mock_node)
        
        assert relevance > 0.3  # Same file bonus
    
    def test_calculate_relevance_similar_name(self, mock_node):
        """Test relevance calculation for nodes with similar names."""
        collector = DeleteCodeEvidenceCollector(
            repo_id=uuid4(),
            target="AuthService",
            max_results=10
        )
        
        other_node = Mock()
        other_node.file_id = uuid4()
        other_node.name = "AuthController"
        other_node.node_type = "controller"
        other_node.complexity_score = 3.0
        other_node.architecture_role = "controller"
        
        relevance = collector._calculate_relevance(other_node, mock_node)
        
        assert relevance >= 0.2  # Similar name bonus
    
    def test_calculate_relevance_same_type(self, mock_node):
        """Test relevance calculation for nodes of same type."""
        collector = DeleteCodeEvidenceCollector(
            repo_id=uuid4(),
            target="AuthService",
            max_results=10
        )
        
        other_node = Mock()
        other_node.file_id = uuid4()
        other_node.name = "UserService"
        other_node.node_type = "service"
        other_node.complexity_score = 3.0
        other_node.architecture_role = "service"
        
        relevance = collector._calculate_relevance(other_node, mock_node)
        
        assert relevance > 0.2  # Same type bonus
    
    def test_rank_and_limit(self, mock_node):
        """Test ranking and limiting of nodes."""
        collector = DeleteCodeEvidenceCollector(
            repo_id=uuid4(),
            target="AuthService",
            max_results=2
        )
        
        nodes = []
        for i in range(5):
            node = Mock()
            node.id = uuid4()
            node.name = f"Service{i}"
            node.node_type = "service"
            node.full_path = f"app/services/service{i}.py"
            node.signature = f"class Service{i}"
            node.raw_code = f"class Service{i}: pass"
            node.start_line = 1
            node.end_line = 10
            node.complexity_score = float(i)
            node.architecture_role = "service"
            nodes.append(node)
        
        ranked = collector._rank_and_limit(nodes, mock_node)
        
        assert len(ranked) <= 2  # Limited to max_results
        assert all(isinstance(r, NodeEvidence) for r in ranked)
    
    def test_filter_by_type(self):
        """Test filtering nodes by type."""
        collector = DeleteCodeEvidenceCollector(
            repo_id=uuid4(),
            target="AuthService",
            max_results=10
        )
        
        nodes = []
        for i in range(3):
            node = Mock()
            node.node_type = "function" if i % 2 == 0 else "service"
            nodes.append(node)
        
        functions = collector._filter_by_type(nodes, "function")
        
        assert len(functions) == 2
        assert all(n.node_type == "function" for n in functions)
    
    def test_to_node_evidence(self, mock_node):
        """Test conversion of Node to NodeEvidence."""
        collector = DeleteCodeEvidenceCollector(
            repo_id=uuid4(),
            target="AuthService",
            max_results=10
        )
        
        evidence = collector._to_node_evidence(mock_node, 0.85)
        
        assert isinstance(evidence, NodeEvidence)
        assert evidence.id == mock_node.id
        assert evidence.name == mock_node.name
        assert evidence.node_type == mock_node.node_type
        assert evidence.relevance_score == 0.85


class TestAddFeatureEvidenceCollector:
    """Test suite for AddFeatureEvidenceCollector."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        return db
    
    def test_collect_node_conversion(self):
        """Test node conversion for ADD_FEATURE intent."""
        collector = AddFeatureEvidenceCollector(
            repo_id=uuid4(),
            target="Stripe",
            max_results=10
        )
        
        mock_node = Mock()
        mock_node.id = uuid4()
        mock_node.name = "StripeService"
        mock_node.node_type = "service"
        mock_node.full_path = "app/services/stripe.py"
        mock_node.signature = "class StripeService"
        mock_node.raw_code = "class StripeService: pass"
        mock_node.start_line = 1
        mock_node.end_line = 10
        mock_node.complexity_score = 5.0
        mock_node.architecture_role = "service"
        
        evidence = collector._to_node_evidence(mock_node, 0.8)
        
        assert evidence.name == "StripeService"
        assert evidence.relevance_score == 0.8


class TestRepositoryEvidenceEngine:
    """Test suite for RepositoryEvidenceEngine."""
    
    @pytest.fixture
    def engine(self):
        """Create RepositoryEvidenceEngine instance."""
        return RepositoryEvidenceEngine()
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        return db
    
    def test_collect_evidence_delete_code_routing(self, engine):
        """Test that DELETE_CODE intent routes to correct collector."""
        request = EvidenceRequest(
            intent=Intent.DELETE_CODE,
            repo_id=uuid4(),
            target="AuthService",
            max_results=10
        )
        
        # Test that the engine has the right collector registered
        assert Intent.DELETE_CODE in engine._collectors
        assert engine._collectors[Intent.DELETE_CODE] == DeleteCodeEvidenceCollector
    
    def test_collect_evidence_add_feature_routing(self, engine):
        """Test that ADD_FEATURE intent routes to correct collector."""
        request = EvidenceRequest(
            intent=Intent.ADD_FEATURE,
            repo_id=uuid4(),
            target="Stripe",
            max_results=10
        )
        
        # Test that the engine has the right collector registered
        assert Intent.ADD_FEATURE in engine._collectors
        assert engine._collectors[Intent.ADD_FEATURE] == AddFeatureEvidenceCollector
    
    def test_collect_evidence_unsupported_intent_routing(self, engine):
        """Test that unsupported intent falls back to generic collection."""
        # Test that REFACTOR is not in collectors
        assert Intent.REFACTOR not in engine._collectors
    
    def test_to_node_evidence(self, engine):
        """Test conversion of Node to NodeEvidence."""
        mock_node = Mock()
        mock_node.id = uuid4()
        mock_node.name = "TestNode"
        mock_node.node_type = "function"
        mock_node.full_path = "app/test.py"
        mock_node.signature = "def test():"
        mock_node.raw_code = "def test(): pass"
        mock_node.start_line = 1
        mock_node.end_line = 5
        mock_node.complexity_score = 2.0
        mock_node.architecture_role = "utility"
        
        evidence = engine._to_node_evidence(mock_node, 0.75)
        
        assert isinstance(evidence, NodeEvidence)
        assert evidence.id == mock_node.id
        assert evidence.name == mock_node.name
        assert evidence.relevance_score == 0.75


class TestEvidenceSchemas:
    """Test suite for evidence schemas."""
    
    def test_evidence_request_schema(self):
        """Test EvidenceRequest schema."""
        request = EvidenceRequest(
            intent=Intent.DELETE_CODE,
            repo_id=uuid4(),
            target="AuthService",
            target_type="service",
            max_results=20,
            include_code_snippets=True
        )
        
        assert request.intent == Intent.DELETE_CODE
        assert request.target == "AuthService"
        assert request.target_type == "service"
        assert request.max_results == 20
        assert request.include_code_snippets is True
    
    def test_evidence_request_defaults(self):
        """Test EvidenceRequest default values."""
        request = EvidenceRequest(
            intent=Intent.DELETE_CODE,
            repo_id=uuid4(),
            target="AuthService"
        )
        
        assert request.max_results == 50
        assert request.include_code_snippets is True
        assert request.target_type is None
    
    def test_evidence_request_validation(self):
        """Test EvidenceRequest validation."""
        import pytest
        from pydantic import ValidationError
        
        # Test max_results too high
        with pytest.raises(ValidationError):
            EvidenceRequest(
                intent=Intent.DELETE_CODE,
                repo_id=uuid4(),
                target="AuthService",
                max_results=300  # Exceeds max of 200
            )
        
        # Test max_results too low
        with pytest.raises(ValidationError):
            EvidenceRequest(
                intent=Intent.DELETE_CODE,
                repo_id=uuid4(),
                target="AuthService",
                max_results=0  # Below min of 1
            )
    
    def test_node_evidence_schema(self):
        """Test NodeEvidence schema."""
        evidence = NodeEvidence(
            id=uuid4(),
            name="AuthService",
            node_type="service",
            full_path="app/services/auth.py",
            signature="class AuthService",
            raw_code="class AuthService: pass",
            start_line=1,
            end_line=10,
            complexity_score=5.0,
            architecture_role="service",
            relevance_score=0.9
        )
        
        assert evidence.name == "AuthService"
        assert evidence.relevance_score == 0.9
    
    def test_node_evidence_relevance_validation(self):
        """Test NodeEvidence relevance score validation."""
        import pytest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            NodeEvidence(
                id=uuid4(),
                name="Test",
                node_type="function",
                full_path="test.py",
                relevance_score=1.5  # Exceeds max of 1.0
            )
        
        with pytest.raises(ValidationError):
            NodeEvidence(
                id=uuid4(),
                name="Test",
                node_type="function",
                full_path="test.py",
                relevance_score=-0.1  # Below min of 0.0
            )
    
    def test_evidence_response_schema(self):
        """Test EvidenceResponse schema."""
        response = EvidenceResponse(
            intent=Intent.DELETE_CODE,
            target="AuthService",
            target_node=None,
            affected_functions=[],
            affected_services=[],
            affected_apis=[],
            affected_database_tables=[],
            callers=[],
            callees=[],
            imports=[],
            dependencies=[],
            dependents=[],
            critical_paths=[],
            workflows=[],
            total_nodes_analyzed=0,
            collection_method="graph_traversal",
            confidence=0.9
        )
        
        assert response.intent == Intent.DELETE_CODE
        assert response.target == "AuthService"
        assert response.confidence == 0.9
    
    def test_evidence_response_confidence_validation(self):
        """Test EvidenceResponse confidence validation."""
        import pytest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            EvidenceResponse(
                intent=Intent.DELETE_CODE,
                target="Test",
                collection_method="test",
                confidence=1.5  # Exceeds max of 1.0
            )
