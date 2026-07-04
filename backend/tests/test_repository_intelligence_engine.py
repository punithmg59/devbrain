import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models import Node, Edge, Workflow
from app.services.intent.schemas import Intent, IntentType, TargetType
from app.services.repository_intelligence import (
    RepositoryIntelligenceEngine,
    EvidenceCategory,
)
from app.services.repository_intelligence.evidence_collector import (
    DeleteEvidenceCollector,
    AddFeatureEvidenceCollector,
    ExplainEvidenceCollector,
    RenameEvidenceCollector,
    RefactorEvidenceCollector,
    DependencyEvidenceCollector,
    ArchitectureEvidenceCollector,
    PlanningEvidenceCollector,
    UnknownEvidenceCollector,
)


@pytest.fixture
def repo_id():
    return uuid.uuid4()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    # By default, db.execute returns an object where .scalars().all() returns empty list
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    db.execute.return_value = mock_result
    return db


def create_mock_result(items):
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = items
    mock_result.scalars.return_value = mock_scalars
    return mock_result


@pytest.mark.asyncio
async def test_delete_service_evidence(repo_id, mock_db):
    engine = RepositoryIntelligenceEngine()
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

    # Setup mock data
    target_node = Node(id=uuid.uuid4(), name="UserService", node_type="service", repo_id=repo_id, full_path="a", complexity_score=10)
    caller_node = Node(id=uuid.uuid4(), name="UserController", node_type="class", repo_id=repo_id, full_path="b", complexity_score=5)
    
    mock_db.execute.side_effect = [
        create_mock_result([target_node]),           # _find_target_nodes
        create_mock_result([Edge(id=uuid.uuid4(), from_node_id=caller_node.id, to_node_id=target_node.id, edge_type="calls", weight=1.0)]), # incoming
        create_mock_result([]),                      # outgoing
        create_mock_result([caller_node]),           # _get_nodes_by_ids
        create_mock_result([]),                      # workflows (WorkflowNode)
    ]

    result = await engine.collect_evidence(repo_id, intent, mock_db)
    
    assert result.intent_type == "DELETE"
    assert result.target_name == "UserService"
    assert result.has_callers is True
    assert len(result.evidence.items[EvidenceCategory.CALLER.value]) == 1
    assert result.evidence.items[EvidenceCategory.CALLER.value][0].name == "UserController"


@pytest.mark.asyncio
async def test_add_feature_evidence(repo_id, mock_db):
    engine = RepositoryIntelligenceEngine()
    intent = Intent(
        intent=IntentType.ADD_FEATURE,
        target_name="PaymentService",
        target_type=TargetType.SERVICE,
        confidence=0.9,
        requires_graph=True,
        requires_llm=False,
        extracted_entities=[],
        raw_question="Add PaymentService",
        normalized_question="Add PaymentService",
        reasoning="",
    )

    pattern_node = Node(id=uuid.uuid4(), name="StripePayment", node_type="class", repo_id=repo_id, full_path="", complexity_score=10)
    service_node = Node(id=uuid.uuid4(), name="AuthService", node_type="service", repo_id=repo_id, full_path="", complexity_score=20)
    api_node = Node(id=uuid.uuid4(), name="/pay", node_type="api_route", repo_id=repo_id, full_path="", complexity_score=5)
    model_node = Node(id=uuid.uuid4(), name="Transaction", node_type="model", repo_id=repo_id, full_path="", complexity_score=15)
    
    mock_db.execute.side_effect = [
        create_mock_result([pattern_node]), # _find_target_nodes
        create_mock_result([service_node]), # services
        create_mock_result([api_node]),     # apis
        create_mock_result([model_node]),   # models
    ]

    result = await engine.collect_evidence(repo_id, intent, mock_db)
    
    assert result.has_apis is True
    assert result.has_database is True
    assert len(result.evidence.items[EvidenceCategory.PATTERN.value]) == 1
    assert len(result.evidence.items[EvidenceCategory.INTEGRATION_POINT.value]) == 1


@pytest.mark.asyncio
async def test_dependency_evidence(repo_id, mock_db):
    engine = RepositoryIntelligenceEngine()
    intent = Intent(
        intent=IntentType.DEPENDENCY,
        target_name="DatabaseClient",
        target_type=TargetType.CLASS,
        confidence=0.9,
        requires_graph=True,
        requires_llm=False,
        extracted_entities=[],
        raw_question="",
        normalized_question="",
        reasoning="",
    )

    target_node = Node(id=uuid.uuid4(), name="DatabaseClient", node_type="class", repo_id=repo_id, full_path="", complexity_score=10)
    callee_node = Node(id=uuid.uuid4(), name="pg_driver", node_type="module", repo_id=repo_id, full_path="", complexity_score=5)
    
    mock_db.execute.side_effect = [
        create_mock_result([target_node]),           # _find_target_nodes
        create_mock_result([]),                      # incoming
        create_mock_result([Edge(id=uuid.uuid4(), from_node_id=target_node.id, to_node_id=callee_node.id, edge_type="imports", weight=1.0)]), # outgoing
        create_mock_result([callee_node]),           # _get_nodes_by_ids
        create_mock_result([]),                      # workflows
    ]

    result = await engine.collect_evidence(repo_id, intent, mock_db)
    
    # Recategorized callees to DEPENDENCY
    assert result.has_callees is False
    assert len(result.evidence.items[EvidenceCategory.DEPENDENCY.value]) == 1


@pytest.mark.asyncio
async def test_evidence_ranker(repo_id, mock_db):
    engine = RepositoryIntelligenceEngine(max_per_category=2)
    intent = Intent(
        intent=IntentType.EXPLAIN,
        target_name="Core",
        target_type=TargetType.MODULE,
        confidence=0.9,
        requires_graph=True,
        requires_llm=False,
        extracted_entities=[],
        raw_question="",
        normalized_question="",
        reasoning="",
    )

    target_node = Node(id=uuid.uuid4(), name="Core", node_type="module", repo_id=repo_id, full_path="", complexity_score=10)
    # n1 has high complexity, n2 has low
    n1 = Node(id=uuid.uuid4(), name="N1", node_type="class", repo_id=repo_id, full_path="", complexity_score=100)
    n2 = Node(id=uuid.uuid4(), name="N2", node_type="class", repo_id=repo_id, full_path="", complexity_score=0)
    n3 = Node(id=uuid.uuid4(), name="N3", node_type="class", repo_id=repo_id, full_path="", complexity_score=50)
    
    mock_db.execute.side_effect = [
        create_mock_result([target_node]),
        create_mock_result([]), # incoming
        create_mock_result([
            Edge(id=uuid.uuid4(), from_node_id=target_node.id, to_node_id=n1.id, edge_type="", weight=1.0),
            Edge(id=uuid.uuid4(), from_node_id=target_node.id, to_node_id=n2.id, edge_type="", weight=1.0),
            Edge(id=uuid.uuid4(), from_node_id=target_node.id, to_node_id=n3.id, edge_type="", weight=1.0),
        ]), # outgoing
        create_mock_result([n1, n2, n3]), # get_nodes_by_ids
        create_mock_result([]), # workflows
    ]

    result = await engine.collect_evidence(repo_id, intent, mock_db)
    
    # Should only keep 2 out of 3, N1 should be first, N3 should be second
    callees = result.evidence.items[EvidenceCategory.CALLEE.value]
    assert len(callees) == 2
    assert callees[0].name == "N1"
    assert callees[1].name == "N3"


@pytest.mark.asyncio
async def test_evidence_scorer(repo_id, mock_db):
    engine = RepositoryIntelligenceEngine()
    intent = Intent(
        intent=IntentType.UNKNOWN,
        target_name="X",
        target_type=TargetType.UNKNOWN,
        confidence=0.9,
        requires_graph=True,
        requires_llm=False,
        extracted_entities=[],
        raw_question="",
        normalized_question="",
        reasoning="",
    )

    # Empty result
    mock_db.execute.return_value = create_mock_result([])
    result = await engine.collect_evidence(repo_id, intent, mock_db)
    
    assert result.score.overall_confidence == 0.0
    assert result.score.coverage_score == 0.0


@pytest.mark.asyncio
async def test_empty_repo(repo_id, mock_db):
    engine = RepositoryIntelligenceEngine()
    intent = Intent(
        intent=IntentType.DELETE,
        target_name="NonExistent",
        target_type=TargetType.SERVICE,
        confidence=0.9,
        requires_graph=True,
        requires_llm=False,
        extracted_entities=[],
        raw_question="",
        normalized_question="",
        reasoning="",
    )

    mock_db.execute.return_value = create_mock_result([])
    result = await engine.collect_evidence(repo_id, intent, mock_db)
    
    assert result.has_callers is False
    assert result.score.overall_confidence == 0.0
