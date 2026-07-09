"""
Test suite for Engineering Intelligence Service
"""

import pytest
from unittest.mock import MagicMock
from app.services.engineering_intelligence_service import EngineeringIntelligenceService
from app.schemas.engineering_intelligence import (
    EngineeringIntelligenceResponse,
    EngineeringDecision,
    EngineeringEvidence,
    RepositoryAnalysis,
    RiskAssessment,
    ImplementationPlan,
    TestingChecklist
)
from app.services.intent.schemas import IntentType
from app.services.engineering_evidence.models import EngineeringEvidence as RepoEvidence, ASTNode, DependencyGraph, CallGraph


class TestEngineeringIntelligenceService:
    """Test suite for Engineering Intelligence Service."""
    
    @pytest.fixture
    def engineering_intelligence_service(self):
        """Create Engineering Intelligence Service instance."""
        return EngineeringIntelligenceService()
    
    @pytest.fixture
    def mock_repo_evidence(self):
        """Create mock repository evidence."""
        return RepoEvidence(
            target_id="test-id",
            target_name="AuthService",
            target_type="service",
            repo_id="repo-id",
            ast_nodes=[
                ASTNode(node_type="class", name="AuthService", file_path="auth.py", line_number=10)
            ],
            dependency_graph=DependencyGraph(nodes=["AuthService"], edges=[], total_nodes=1, total_edges=0),
            call_graph=CallGraph(function_calls=[], call_depth=0, entry_points=[]),
            classes=[],
            functions=[],
            api_routes=[],
            imports=[],
            overall_summary="Test evidence",
            evidence_confidence=0.8
        )
    
    def test_generate_engineering_decision_delete(self, engineering_intelligence_service, mock_repo_evidence):
        """Test engineering decision generation for DELETE intent."""
        engine_result = {"summary": "Test result", "processing_time_ms": 50}
        
        decision = engineering_intelligence_service._generate_engineering_decision(
            IntentType.DELETE,
            "AuthService",
            mock_repo_evidence,
            engine_result
        )
        
        assert isinstance(decision, EngineeringDecision)
        assert "delete" in decision.decision.lower()
        assert decision.confidence == 0.8
        assert len(decision.alternatives) > 0
    
    def test_generate_engineering_decision_refactor(self, engineering_intelligence_service, mock_repo_evidence):
        """Test engineering decision generation for REFACTOR intent."""
        engine_result = {"summary": "Test result", "processing_time_ms": 50}
        
        decision = engineering_intelligence_service._generate_engineering_decision(
            IntentType.REFACTOR,
            "AuthService",
            mock_repo_evidence,
            engine_result
        )
        
        assert isinstance(decision, EngineeringDecision)
        assert "refactor" in decision.decision.lower()
        assert decision.confidence == 0.8
    
    def test_generate_engineering_evidence(self, engineering_intelligence_service, mock_repo_evidence):
        """Test engineering evidence generation."""
        evidence = engineering_intelligence_service._generate_engineering_evidence(mock_repo_evidence)
        
        assert isinstance(evidence, EngineeringEvidence)
        assert evidence.evidence_confidence == 0.8
        assert len(evidence.data_sources) > 0
        assert "AST analysis" in evidence.data_sources
    
    def test_generate_repository_analysis(self, engineering_intelligence_service, mock_repo_evidence):
        """Test repository analysis generation."""
        analysis = engineering_intelligence_service._generate_repository_analysis(mock_repo_evidence)
        
        assert isinstance(analysis, RepositoryAnalysis)
        assert analysis.structure_summary
        assert "total_classes" in analysis.code_metrics
        assert "total_functions" in analysis.code_metrics
    
    def test_identify_affected_components(self, engineering_intelligence_service, mock_repo_evidence):
        """Test affected components identification."""
        # Add some classes and functions to the evidence
        mock_repo_evidence.classes = [
            MagicMock(name="UserService", file_path="user.py"),
            MagicMock(name="PaymentService", file_path="payment.py")
        ]
        mock_repo_evidence.functions = [
            MagicMock(name="authenticate", file_path="auth.py"),
            MagicMock(name="authorize", file_path="auth.py")
        ]
        
        engine_result = {"summary": "Test result"}
        
        affected = engineering_intelligence_service._identify_affected_components(
            IntentType.DELETE,
            "AuthService",
            mock_repo_evidence,
            engine_result
        )
        
        assert len(affected) > 0
        assert all(comp.impact_level in ["critical", "high", "medium", "low"] for comp in affected)
    
    def test_generate_risk_assessment_high_risk(self, engineering_intelligence_service, mock_repo_evidence):
        """Test risk assessment for high-risk scenario."""
        from app.schemas.engineering_intelligence import AffectedComponent
        
        # Create high-risk affected components
        affected_components = [
            AffectedComponent(
                name="CriticalComponent",
                type="service",
                file_path="critical.py",
                impact_level="critical",
                impact_description="Critical impact",
                required_changes=["Fix"]
            ),
            AffectedComponent(
                name="HighComponent",
                type="service",
                file_path="high.py",
                impact_level="high",
                impact_description="High impact",
                required_changes=["Fix"]
            )
        ]
        
        risk = engineering_intelligence_service._generate_risk_assessment(
            IntentType.DELETE,
            "AuthService",
            mock_repo_evidence,
            affected_components
        )
        
        assert isinstance(risk, RiskAssessment)
        assert risk.overall_risk in ["critical", "high", "medium", "low"]
        assert risk.probability_of_failure > 0
        assert len(risk.mitigation_strategies) > 0
    
    def test_generate_risk_assessment_low_risk(self, engineering_intelligence_service, mock_repo_evidence):
        """Test risk assessment for low-risk scenario."""
        from app.schemas.engineering_intelligence import AffectedComponent
        
        # Create low-risk affected components
        affected_components = [
            AffectedComponent(
                name="LowComponent",
                type="function",
                file_path="low.py",
                impact_level="low",
                impact_description="Low impact",
                required_changes=["Review"]
            )
        ]
        
        risk = engineering_intelligence_service._generate_risk_assessment(
            IntentType.MODIFY,
            "AuthService",
            mock_repo_evidence,
            affected_components
        )
        
        assert isinstance(risk, RiskAssessment)
        assert risk.overall_risk == "low"
        assert risk.probability_of_failure < 0.5
    
    def test_generate_recommended_changes(self, engineering_intelligence_service, mock_repo_evidence):
        """Test recommended changes generation."""
        engine_result = {"summary": "Test result"}
        
        changes = engineering_intelligence_service._generate_recommended_changes(
            IntentType.DELETE,
            "AuthService",
            mock_repo_evidence,
            engine_result
        )
        
        assert len(changes) > 0
        assert all(change.priority in ["critical", "high", "medium", "low"] for change in changes)
        assert all(change.effort_estimate for change in changes)
    
    def test_generate_implementation_plan(self, engineering_intelligence_service, mock_repo_evidence):
        """Test implementation plan generation."""
        from app.schemas.engineering_intelligence import RecommendedChange
        
        recommended_changes = [
            RecommendedChange(
                description="Test change",
                priority="high",
                effort_estimate="2 hours"
            )
        ]
        
        plan = engineering_intelligence_service._generate_implementation_plan(
            IntentType.DELETE,
            "AuthService",
            mock_repo_evidence,
            recommended_changes
        )
        
        assert isinstance(plan, ImplementationPlan)
        assert len(plan.phases) > 0
        assert len(plan.steps) > 0
        assert plan.total_estimated_time
        assert len(plan.prerequisites) > 0
        assert plan.rollback_plan
    
    def test_generate_testing_checklist(self, engineering_intelligence_service, mock_repo_evidence):
        """Test testing checklist generation."""
        from app.schemas.engineering_intelligence import ImplementationPlan
        
        implementation_plan = ImplementationPlan(
            phases=["Test"],
            steps=[],
            total_estimated_time="1 hour",
            prerequisites=[],
            rollback_plan="Test rollback"
        )
        
        checklist = engineering_intelligence_service._generate_testing_checklist(
            IntentType.DELETE,
            "AuthService",
            mock_repo_evidence,
            implementation_plan
        )
        
        assert isinstance(checklist, TestingChecklist)
        assert len(checklist.unit_tests) > 0
        assert len(checklist.integration_tests) > 0
        assert checklist.total_test_count > 0
        assert checklist.coverage_target > 0
    
    def test_generate_engineering_actions(self, engineering_intelligence_service):
        """Test engineering actions generation."""
        from app.schemas.engineering_intelligence import RecommendedChange, ImplementationPlan
        
        recommended_changes = [
            RecommendedChange(
                description="Test change",
                priority="high",
                effort_estimate="2 hours"
            )
        ]
        
        implementation_plan = ImplementationPlan(
            phases=["Test"],
            steps=[],
            total_estimated_time="1 hour",
            prerequisites=[],
            rollback_plan="Test rollback"
        )
        
        actions = engineering_intelligence_service._generate_engineering_actions(
            IntentType.DELETE,
            "AuthService",
            recommended_changes,
            implementation_plan
        )
        
        assert len(actions) > 0
        assert all(action.action_type for action in actions)
        assert all(action.priority for action in actions)
    
    def test_generate_intelligence_response_complete(self, engineering_intelligence_service, mock_repo_evidence):
        """Test complete engineering intelligence response generation."""
        engine_result = {
            "summary": "Test summary",
            "evidence": {},
            "processing_time_ms": 100
        }
        
        response = engineering_intelligence_service.generate_intelligence_response(
            question="What breaks if I delete AuthService?",
            intent=IntentType.DELETE,
            target_name="AuthService",
            repo_evidence=mock_repo_evidence,
            engine_result=engine_result
        )
        
        assert isinstance(response, EngineeringIntelligenceResponse)
        assert response.question == "What breaks if I delete AuthService?"
        assert response.intent == "DELETE"
        assert response.target_name == "AuthService"
        assert isinstance(response.engineering_decision, EngineeringDecision)
        assert isinstance(response.engineering_evidence, EngineeringEvidence)
        assert isinstance(response.repository_analysis, RepositoryAnalysis)
        assert isinstance(response.risk_assessment, RiskAssessment)
        assert isinstance(response.implementation_plan, ImplementationPlan)
        assert isinstance(response.testing_checklist, TestingChecklist)
        assert response.grounded_in_repository == True
        assert response.evidence_confidence == 0.8
    
    def test_parse_time_to_hours(self, engineering_intelligence_service):
        """Test time parsing utility."""
        assert engineering_intelligence_service._parse_time_to_hours("2 hours") == 2.0
        assert engineering_intelligence_service._parse_time_to_hours("30 minutes") == 0.5
        assert engineering_intelligence_service._parse_time_to_hours("1 hour") == 1.0
