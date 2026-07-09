"""Unit tests for Engineering Evidence Engine."""

import pytest
from uuid import uuid4

from app.services.engineering_evidence.models import (
    EngineeringEvidence,
    EvidenceGroup,
    EvidenceCategory,
    FailureMode,
    RiskCategory,
    RiskAssessment,
    Criticality,
)
from app.services.engineering_evidence.grouping_logic import GroupingLogic
from app.services.engineering_evidence.scoring_logic import ScoringLogic
from app.services.engineering_evidence.engineering_evidence_engine import EngineeringEvidenceEngine
from app.services.reference_intelligence.models import (
    Reference,
    ReferenceType,
    ReferenceLocation,
    ReferenceAnalysisResult,
)


class TestGroupingLogic:
    """Test grouping logic for evidence categories."""

    def test_group_references_empty(self):
        """Test grouping empty references."""
        grouped = GroupingLogic.group_references([])
        assert len(grouped) == 8
        assert all(len(refs) == 0 for refs in grouped.values())

    def test_group_references_runtime(self):
        """Test grouping runtime references."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.HIGH,
                provider="AuthService",
            ),
            Reference(
                reference_type=ReferenceType.FASTAPI_ROUTE,
                reference_location=ReferenceLocation.RUNTIME,
                file_path="routes.py",
                line_number=5,
                confidence=0.8,
                criticality=Criticality.CRITICAL,
                provider="login_route",
            ),
        ]
        grouped = GroupingLogic.group_references(references)
        assert len(grouped[EvidenceCategory.RUNTIME]) == 1
        assert len(grouped[EvidenceCategory.PUBLIC_API]) == 1

    def test_group_references_configuration(self):
        """Test grouping configuration references."""
        references = [
            Reference(
                reference_type=ReferenceType.ENV_VAR,
                reference_location=ReferenceLocation.CONFIGURATION,
                file_path=".env",
                line_number=1,
                confidence=0.9,
                criticality=Criticality.MEDIUM,
                provider="DATABASE_URL",
            ),
            Reference(
                reference_type=ReferenceType.YAML_CONFIG,
                reference_location=ReferenceLocation.CONFIGURATION,
                file_path="config.yaml",
                line_number=5,
                confidence=0.8,
                criticality=Criticality.LOW,
                provider="api_config",
            ),
        ]
        grouped = GroupingLogic.group_references(references)
        assert len(grouped[EvidenceCategory.CONFIGURATION]) == 2

    def test_group_references_database(self):
        """Test grouping database references."""
        references = [
            Reference(
                reference_type=ReferenceType.ORM_MODEL,
                reference_location=ReferenceLocation.DATABASE,
                file_path="models.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="User",
            ),
            Reference(
                reference_type=ReferenceType.FOREIGN_KEY,
                reference_location=ReferenceLocation.DATABASE,
                file_path="models.py",
                line_number=15,
                confidence=0.8,
                criticality=Criticality.HIGH,
                provider="user_id",
            ),
        ]
        grouped = GroupingLogic.group_references(references)
        assert len(grouped[EvidenceCategory.DATABASE]) == 2

    def test_determine_failure_mode_runtime(self):
        """Test failure mode determination for runtime."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="AuthService",
            ),
        ]
        failure_mode = GroupingLogic.determine_failure_mode(
            EvidenceCategory.RUNTIME, references
        )
        assert failure_mode == FailureMode.RUNTIME_ERROR

    def test_determine_failure_mode_configuration(self):
        """Test failure mode determination for configuration."""
        references = [
            Reference(
                reference_type=ReferenceType.ENV_VAR,
                reference_location=ReferenceLocation.CONFIGURATION,
                file_path=".env",
                line_number=1,
                confidence=0.9,
                criticality=Criticality.MEDIUM,
                provider="DATABASE_URL",
            ),
        ]
        failure_mode = GroupingLogic.determine_failure_mode(
            EvidenceCategory.CONFIGURATION, references
        )
        assert failure_mode == FailureMode.CONFIGURATION_ERROR

    def test_extract_affected_systems(self):
        """Test extraction of affected systems."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="auth_service/auth.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.HIGH,
                provider="AuthService",
                consumer="UserController",
            ),
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="api_service/api.py",
                line_number=5,
                confidence=0.8,
                criticality=Criticality.MEDIUM,
                provider="AuthService",
                consumer="APIController",
            ),
        ]
        systems = GroupingLogic.extract_affected_systems(references)
        assert "UserController" in systems
        assert "APIController" in systems
        assert "auth_service" in systems
        assert "api_service" in systems


class TestScoringLogic:
    """Test scoring logic for evidence groups."""

    def test_calculate_criticality_critical(self):
        """Test criticality calculation with critical references."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="AuthService",
            ),
        ]
        criticality = ScoringLogic.calculate_criticality(references)
        assert criticality == Criticality.CRITICAL

    def test_calculate_criticality_high(self):
        """Test criticality calculation with high references."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.HIGH,
                provider="AuthService",
            ),
        ]
        criticality = ScoringLogic.calculate_criticality(references)
        assert criticality == Criticality.HIGH

    def test_calculate_criticality_medium(self):
        """Test criticality calculation with many low references."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=i,
                confidence=0.9,
                criticality=Criticality.LOW,
                provider=f"Service{i}",
            )
            for i in range(15)
        ]
        criticality = ScoringLogic.calculate_criticality(references)
        assert criticality == Criticality.MEDIUM

    def test_calculate_impact_score(self):
        """Test impact score calculation."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=i,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider=f"Service{i}",
            )
            for i in range(10)
        ]
        impact_score = ScoringLogic.calculate_impact_score(
            references, EvidenceCategory.RUNTIME
        )
        assert 0.0 <= impact_score <= 1.0
        assert impact_score > 0.3  # Should be moderate due to critical references

    def test_calculate_confidence(self):
        """Test confidence calculation."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=i,
                confidence=0.8,
                criticality=Criticality.HIGH,
                provider=f"Service{i}",
            )
            for i in range(10)
        ]
        confidence = ScoringLogic.calculate_confidence(references)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.8  # Should be high due to many references

    def test_generate_engineering_summary(self):
        """Test engineering summary generation."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="AuthService",
            ),
        ]
        summary = ScoringLogic.generate_engineering_summary(
            EvidenceCategory.RUNTIME,
            references,
            Criticality.CRITICAL,
            0.9,
        )
        assert "runtime" in summary.lower()
        assert "critical" in summary.lower()

    def test_generate_overall_summary(self):
        """Test overall summary generation."""
        evidence_groups = {
            EvidenceCategory.RUNTIME: [
                Reference(
                    reference_type=ReferenceType.FUNCTION_CALL,
                    reference_location=ReferenceLocation.SOURCE_CODE,
                    file_path="test.py",
                    line_number=10,
                    confidence=0.9,
                    criticality=Criticality.CRITICAL,
                    provider="AuthService",
                ),
            ],
            EvidenceCategory.DATABASE: [],
        }
        summary = ScoringLogic.generate_overall_summary(evidence_groups)
        assert "1" in summary or "references" in summary.lower()

    def test_generate_risk_assessment(self):
        """Test risk assessment generation."""
        risk_assessment = ScoringLogic.generate_risk_assessment(
            RiskCategory.RUNTIME,
            Criticality.CRITICAL,
            0.9,
            ["AuthService", "UserController"],
            FailureMode.RUNTIME_ERROR,
        )
        assert risk_assessment.category == RiskCategory.RUNTIME
        assert risk_assessment.risk_level == Criticality.CRITICAL
        assert risk_assessment.risk_score > 0.8
        assert "AuthService" in risk_assessment.affected_systems

    def test_generate_critical_findings(self):
        """Test critical findings generation."""
        evidence_groups = {
            EvidenceCategory.RUNTIME: EvidenceGroup(
                category=EvidenceCategory.RUNTIME,
                references=[],
                criticality=Criticality.CRITICAL,
                impact_score=0.9,
                confidence=0.9,
                engineering_summary="Test",
                estimated_failure_mode=FailureMode.RUNTIME_ERROR,
                risk_drivers=[],
                affected_systems=[],
                critical_count=5,
                high_count=0,
            ),
        }
        findings = ScoringLogic.generate_critical_findings(evidence_groups)
        assert len(findings) > 0
        assert "CRITICAL" in findings[0]

    def test_generate_validation_steps(self):
        """Test validation steps generation."""
        evidence_groups = {
            EvidenceCategory.RUNTIME: EvidenceGroup(
                category=EvidenceCategory.RUNTIME,
                references=[],
                criticality=Criticality.CRITICAL,
                impact_score=0.9,
                confidence=0.9,
                engineering_summary="Test",
                estimated_failure_mode=FailureMode.RUNTIME_ERROR,
                risk_drivers=[],
                affected_systems=[],
                critical_count=5,
                high_count=0,
            ),
        }
        steps = ScoringLogic.generate_validation_steps(
            evidence_groups, Criticality.CRITICAL
        )
        assert len(steps) > 0
        assert any("rollback" in step.lower() for step in steps)


class TestEngineeringEvidenceEngine:
    """Test Engineering Evidence Engine."""

    def test_transform_references_to_evidence_empty(self):
        """Test transformation with empty references."""
        engine = EngineeringEvidenceEngine()
        reference_analysis = ReferenceAnalysisResult(
            target_id=uuid4(),
            target_name="AuthService",
            target_type="service",
            repo_id=uuid4(),
            references=[],
        )
        reference_analysis.calculate_metrics()
        
        evidence = engine.transform_references_to_evidence(reference_analysis)
        assert evidence.target_name == "AuthService"
        assert evidence.total_references == 0
        assert evidence.overall_criticality == Criticality.LOW

    def test_transform_references_to_evidence_with_data(self):
        """Test transformation with actual references."""
        engine = EngineeringEvidenceEngine()
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="auth_service/auth.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="AuthService",
                consumer="UserController",
            ),
            Reference(
                reference_type=ReferenceType.ENV_VAR,
                reference_location=ReferenceLocation.CONFIGURATION,
                file_path=".env",
                line_number=1,
                confidence=0.8,
                criticality=Criticality.MEDIUM,
                provider="DATABASE_URL",
            ),
        ]
        reference_analysis = ReferenceAnalysisResult(
            target_id=uuid4(),
            target_name="AuthService",
            target_type="service",
            repo_id=uuid4(),
            references=references,
        )
        reference_analysis.calculate_metrics()
        
        evidence = engine.transform_references_to_evidence(reference_analysis)
        assert evidence.target_name == "AuthService"
        assert evidence.total_references == 2
        assert evidence.runtime is not None
        assert evidence.configuration is not None
        assert evidence.overall_criticality == Criticality.CRITICAL

    def test_create_evidence_group(self):
        """Test evidence group creation."""
        engine = EngineeringEvidenceEngine()
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="AuthService",
            ),
        ]
        group = engine._create_evidence_group(
            EvidenceCategory.RUNTIME, references
        )
        assert group.category == EvidenceCategory.RUNTIME
        assert group.reference_count == 1
        assert group.criticality == Criticality.CRITICAL
        assert group.impact_score > 0.0
        assert group.confidence > 0.0
        assert len(group.highest_risk_references) == 1


class TestEngineeringEvidenceModels:
    """Test Engineering Evidence models."""

    def test_evidence_group_calculate_metrics(self):
        """Test evidence group metrics calculation."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=i,
                confidence=0.9,
                criticality=Criticality.CRITICAL if i < 3 else Criticality.HIGH,
                provider=f"Service{i}",
            )
            for i in range(5)
        ]
        group = EvidenceGroup(
            category=EvidenceCategory.RUNTIME,
            references=references,
            criticality=Criticality.CRITICAL,
            impact_score=0.9,
            confidence=0.9,
            engineering_summary="Test",
            estimated_failure_mode=FailureMode.RUNTIME_ERROR,
            risk_drivers=[],
            affected_systems=[],
        )
        group.calculate_metrics()
        assert group.reference_count == 5
        assert group.critical_count == 3
        assert group.high_count == 2
        assert len(group.highest_risk_references) == 5

    def test_engineering_evidence_calculate_overall_metrics(self):
        """Test engineering evidence overall metrics calculation."""
        evidence = EngineeringEvidence(
            target_id=uuid4(),
            target_name="AuthService",
            target_type="service",
            repo_id=uuid4(),
            overall_summary="Test",
            evidence_confidence=0.0,
            runtime=EvidenceGroup(
                category=EvidenceCategory.RUNTIME,
                references=[],
                criticality=Criticality.CRITICAL,
                impact_score=0.9,
                confidence=0.9,
                engineering_summary="Test",
                estimated_failure_mode=FailureMode.RUNTIME_ERROR,
                risk_drivers=[],
                affected_systems=["AuthService", "UserController"],
                critical_count=5,
                high_count=0,
            ),
            configuration=EvidenceGroup(
                category=EvidenceCategory.CONFIGURATION,
                references=[],
                criticality=Criticality.MEDIUM,
                impact_score=0.5,
                confidence=0.8,
                engineering_summary="Test",
                estimated_failure_mode=FailureMode.CONFIGURATION_ERROR,
                risk_drivers=[],
                affected_systems=["ConfigService"],
                critical_count=0,
                high_count=2,
            ),
        )
        evidence.calculate_overall_metrics()
        assert evidence.total_references == 0  # Empty references lists
        assert evidence.overall_criticality == Criticality.CRITICAL
        assert evidence.overall_impact_score > 0.0
        assert evidence.overall_confidence > 0.0
        assert "AuthService" in evidence.affected_systems
        assert "UserController" in evidence.affected_systems
        assert "ConfigService" in evidence.affected_systems

    def test_risk_assessment_model(self):
        """Test risk assessment model."""
        risk_assessment = RiskAssessment(
            category=RiskCategory.RUNTIME,
            risk_level=Criticality.CRITICAL,
            risk_score=0.9,
            affected_systems=["AuthService", "UserController"],
            failure_probability=0.85,
            description="Critical runtime risk detected",
        )
        assert risk_assessment.category == RiskCategory.RUNTIME
        assert risk_assessment.risk_level == Criticality.CRITICAL
        assert risk_assessment.risk_score == 0.9
        assert len(risk_assessment.affected_systems) == 2
