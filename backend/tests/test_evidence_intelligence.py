"""Unit tests for Evidence Intelligence Engine."""

import pytest
from uuid import UUID, uuid4

from app.services.reference_intelligence.models import (
    Reference,
    ReferenceType,
    ReferenceLocation,
    Criticality,
    ReferenceAnalysisResult
)
from app.services.engineering_evidence.models import (
    EvidenceCategory,
    FailureMode,
    EvidenceGroup,
    EngineeringEvidence,
    RiskCategory
)
from app.services.engineering_evidence.grouping_logic import GroupingLogic
from app.services.engineering_evidence.scoring_logic import ScoringLogic
from app.services.engineering_evidence.engineering_evidence_engine import EngineeringEvidenceEngine


class TestGroupingLogic:
    """Test reference grouping logic."""
    
    def test_group_runtime_dependencies(self):
        """Test grouping runtime dependencies."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=1,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="AuthService"
            ),
            Reference(
                reference_type=ReferenceType.FASTAPI_ROUTE,
                reference_location=ReferenceLocation.RUNTIME,
                file_path="routes.py",
                line_number=5,
                confidence=0.9,
                criticality=Criticality.HIGH,
                provider="AuthService"
            ),
        ]
        
        groups = GroupingLogic.group_references(references)
        
        assert EvidenceCategory.RUNTIME in groups
        assert len(groups[EvidenceCategory.RUNTIME]) == 1
        assert len(groups[EvidenceCategory.PUBLIC_API]) == 1
    
    def test_group_configuration_dependencies(self):
        """Test grouping configuration dependencies."""
        references = [
            Reference(
                reference_type=ReferenceType.ENV_VAR,
                reference_location=ReferenceLocation.CONFIGURATION,
                file_path=".env",
                line_number=1,
                confidence=0.8,
                criticality=Criticality.HIGH,
                provider="AUTH_SERVICE"
            ),
        ]
        
        groups = GroupingLogic.group_references(references)
        
        assert EvidenceCategory.CONFIGURATION in groups
        assert len(groups[EvidenceCategory.CONFIGURATION]) == 1
    
    def test_group_database_dependencies(self):
        """Test grouping database dependencies."""
        references = [
            Reference(
                reference_type=ReferenceType.SQL_MIGRATION,
                reference_location=ReferenceLocation.DATABASE,
                file_path="migration.sql",
                line_number=1,
                confidence=0.85,
                criticality=Criticality.CRITICAL,
                provider="users"
            ),
            Reference(
                reference_type=ReferenceType.FOREIGN_KEY,
                reference_location=ReferenceLocation.DATABASE,
                file_path="migration.sql",
                line_number=5,
                confidence=0.85,
                criticality=Criticality.HIGH,
                provider="users"
            ),
        ]
        
        groups = GroupingLogic.group_references(references)
        
        assert EvidenceCategory.DATABASE in groups
        assert len(groups[EvidenceCategory.DATABASE]) == 2
    
    def test_determine_failure_mode_runtime(self):
        """Test failure mode determination for runtime dependencies."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=1,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="AuthService"
            ),
        ]
        
        failure_mode = GroupingLogic.determine_failure_mode(
            EvidenceCategory.RUNTIME,
            references
        )
        
        assert failure_mode == FailureMode.RUNTIME_ERROR
    
    def test_determine_failure_mode_database(self):
        """Test failure mode determination for database dependencies."""
        references = [
            Reference(
                reference_type=ReferenceType.FOREIGN_KEY,
                reference_location=ReferenceLocation.DATABASE,
                file_path="migration.sql",
                line_number=1,
                confidence=0.85,
                criticality=Criticality.CRITICAL,
                provider="users"
            ),
        ]
        
        failure_mode = GroupingLogic.determine_failure_mode(
            EvidenceCategory.DATABASE,
            references
        )
        
        assert failure_mode == FailureMode.DATA_CORRUPTION


class TestScoringLogic:
    """Test scoring logic."""
    
    def test_calculate_criticality_critical(self):
        """Test criticality calculation with critical references."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=1,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="AuthService"
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
                line_number=1,
                confidence=0.9,
                criticality=Criticality.HIGH,
                provider="AuthService"
            ),
        ]
        
        criticality = ScoringLogic.calculate_criticality(references)
        assert criticality == Criticality.HIGH
    
    def test_calculate_impact_score(self):
        """Test impact score calculation."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=1,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="AuthService"
            ),
        ] * 20  # 20 references
        
        impact_score = ScoringLogic.calculate_impact_score(
            references,
            EvidenceCategory.RUNTIME
        )
        
        # Should be high due to count and criticality
        assert impact_score > 0.5
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=1,
                confidence=0.9,
                criticality=Criticality.HIGH,
                provider="AuthService"
            ),
        ] * 10  # 10 references
        
        confidence = ScoringLogic.calculate_confidence(references)
        
        # Should be high due to good base confidence and count boost
        assert confidence > 0.8
    
    def test_generate_engineering_summary(self):
        """Test engineering summary generation."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=1,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="AuthService"
            ),
        ]
        
        summary = ScoringLogic.generate_engineering_summary(
            EvidenceCategory.RUNTIME,
            references,
            Criticality.CRITICAL,
            0.9
        )
        
        assert "runtime dependencies" in summary.lower()
        assert "critical" in summary.lower()
    
    def test_generate_overall_summary(self):
        """Test overall summary generation."""
        evidence_groups = {
            EvidenceCategory.RUNTIME: [
                Reference(
                    reference_type=ReferenceType.FUNCTION_CALL,
                    reference_location=ReferenceLocation.SOURCE_CODE,
                    file_path="test.py",
                    line_number=1,
                    confidence=0.9,
                    criticality=Criticality.CRITICAL,
                    provider="AuthService"
                ),
            ],
            EvidenceCategory.DATABASE: [],
        }
        
        summary = ScoringLogic.generate_overall_summary(evidence_groups)
        
        assert "references" in summary.lower()
        assert "critical" in summary.lower()
    
    def test_generate_risk_assessment_critical(self):
        """Test risk assessment for critical criticality."""
        assessment = ScoringLogic.generate_risk_assessment(
            RiskCategory.RUNTIME,
            Criticality.CRITICAL,
            0.9,
            ["AuthService", "UserController"],
            FailureMode.RUNTIME_ERROR,
        )
        
        assert assessment.risk_level == Criticality.CRITICAL
        assert assessment.risk_score > 0.8
    
    def test_generate_risk_assessment_low(self):
        """Test risk assessment for low criticality."""
        assessment = ScoringLogic.generate_risk_assessment(
            RiskCategory.RUNTIME,
            Criticality.LOW,
            0.2,
            [],
            FailureMode.UNKNOWN,
        )
        
        assert assessment.risk_level == Criticality.LOW
        assert assessment.risk_score < 0.5
    
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


class TestEvidenceGroup:
    """Test EvidenceGroup model."""
    
    def test_calculate_metrics(self):
        """Test evidence group metric calculation."""
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=1,
                confidence=0.9,
                criticality=Criticality.CRITICAL,
                provider="AuthService"
            ),
            Reference(
                reference_type=ReferenceType.IMPORT,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=5,
                confidence=0.8,
                criticality=Criticality.HIGH,
                provider="AuthService"
            ),
        ]
        
        group = EvidenceGroup(
            category=EvidenceCategory.RUNTIME,
            references=references,
            criticality=Criticality.CRITICAL,
            impact_score=0.9,
            confidence=0.85,
            engineering_summary="Test",
            estimated_failure_mode=FailureMode.RUNTIME_ERROR
        )
        
        group.calculate_metrics()
        
        assert group.reference_count == 2
        assert group.critical_count == 1
        assert group.high_count == 1
        assert len(group.highest_risk_references) == 2


class TestEngineeringEvidence:
    """Test EngineeringEvidence model."""
    
    def test_calculate_overall_metrics(self):
        """Test overall metric calculation."""
        evidence = EngineeringEvidence(
            target_id=uuid4(),
            target_name="AuthService",
            target_type="service",
            repo_id=uuid4(),
            overall_summary="Test summary",
            evidence_confidence=0.0,
            runtime=EvidenceGroup(
                category=EvidenceCategory.RUNTIME,
                references=[
                    Reference(
                        reference_type=ReferenceType.FUNCTION_CALL,
                        reference_location=ReferenceLocation.SOURCE_CODE,
                        file_path="test.py",
                        line_number=1,
                        confidence=0.9,
                        criticality=Criticality.CRITICAL,
                        provider="AuthService",
                    ),
                ],
                criticality=Criticality.CRITICAL,
                impact_score=0.9,
                confidence=0.9,
                engineering_summary="Test",
                estimated_failure_mode=FailureMode.RUNTIME_ERROR,
                risk_drivers=[],
                affected_systems=[],
                critical_count=1,
                high_count=0,
            )
        )
        
        evidence.runtime.calculate_metrics()
        evidence.calculate_overall_metrics()
        
        assert evidence.total_references == 1
        assert evidence.overall_criticality == Criticality.CRITICAL
        assert evidence.overall_impact_score == 0.9
        assert evidence.overall_confidence == 0.9


class TestEvidenceIntelligenceEngine:
    """Test unified Evidence Intelligence Engine orchestrator."""
    
    def test_transform_references_to_evidence(self):
        """Test transformation from references to evidence."""
        engine = EngineeringEvidenceEngine()
        
        reference_analysis = ReferenceAnalysisResult(
            target_id=uuid4(),
            target_name="AuthService",
            target_type="service",
            repo_id=uuid4(),
            references=[
                Reference(
                    reference_type=ReferenceType.FUNCTION_CALL,
                    reference_location=ReferenceLocation.SOURCE_CODE,
                    file_path="test.py",
                    line_number=1,
                    confidence=0.9,
                    criticality=Criticality.CRITICAL,
                    provider="AuthService"
                ),
                Reference(
                    reference_type=ReferenceType.ENV_VAR,
                    reference_location=ReferenceLocation.CONFIGURATION,
                    file_path=".env",
                    line_number=1,
                    confidence=0.8,
                    criticality=Criticality.HIGH,
                    provider="AUTH_SERVICE"
                ),
            ]
        )
        
        evidence = engine.transform_references_to_evidence(reference_analysis)
        
        assert evidence.target_name == "AuthService"
        assert evidence.total_references == 2
        assert evidence.runtime is not None
        assert evidence.configuration is not None
        assert evidence.overall_summary is not None
        assert evidence.deployment_risk is not None or evidence.runtime_risk is not None
        assert len(evidence.recommended_validation_steps) > 0
    
    def test_transform_empty_references(self):
        """Test transformation with no references."""
        engine = EngineeringEvidenceEngine()
        
        reference_analysis = ReferenceAnalysisResult(
            target_id=uuid4(),
            target_name="AuthService",
            target_type="service",
            repo_id=uuid4(),
            references=[]
        )
        
        evidence = engine.transform_references_to_evidence(reference_analysis)
        
        assert evidence.total_references == 0
        assert evidence.overall_criticality == Criticality.LOW
        assert "no references" in evidence.overall_summary.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
