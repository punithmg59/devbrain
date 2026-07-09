"""Integration tests for Engineering Evidence Engine - DELETE/RENAME/MOVE scenarios."""

import pytest
from uuid import uuid4

from app.services.engineering_evidence.models import (
    EngineeringEvidence,
    EvidenceGroup,
    EvidenceCategory,
    Criticality,
    FailureMode,
)
from app.services.engineering_evidence.engineering_evidence_engine import EngineeringEvidenceEngine
from app.services.reference_intelligence.models import (
    Reference,
    ReferenceType,
    ReferenceLocation,
    ReferenceAnalysisResult,
)


class TestDeleteScenario:
    """Test DELETE scenario evidence generation."""

    def test_delete_critical_service(self):
        """Test DELETE of a critical service with many dependencies."""
        engine = EngineeringEvidenceEngine()
        
        # Simulate a critical service with many dependencies
        references = [
            # Runtime dependencies (function calls)
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="auth_service/auth.py",
                line_number=10,
                confidence=0.95,
                criticality=Criticality.CRITICAL,
                provider="AuthService",
                consumer="UserController",
            ),
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="auth_service/auth.py",
                line_number=15,
                confidence=0.92,
                criticality=Criticality.CRITICAL,
                provider="AuthService",
                consumer="OrderController",
            ),
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="auth_service/auth.py",
                line_number=20,
                confidence=0.88,
                criticality=Criticality.HIGH,
                provider="AuthService",
                consumer="PaymentController",
            ),
            # API routes
            Reference(
                reference_type=ReferenceType.FASTAPI_ROUTE,
                reference_location=ReferenceLocation.RUNTIME,
                file_path="routes/auth.py",
                line_number=5,
                confidence=0.95,
                criticality=Criticality.CRITICAL,
                provider="/api/auth/login",
            ),
            Reference(
                reference_type=ReferenceType.FASTAPI_ROUTE,
                reference_location=ReferenceLocation.RUNTIME,
                file_path="routes/auth.py",
                line_number=10,
                confidence=0.90,
                criticality=Criticality.HIGH,
                provider="/api/auth/logout",
            ),
            # Database dependencies
            Reference(
                reference_type=ReferenceType.ORM_MODEL,
                reference_location=ReferenceLocation.DATABASE,
                file_path="models/user.py",
                line_number=5,
                confidence=0.95,
                criticality=Criticality.CRITICAL,
                provider="User",
            ),
            Reference(
                reference_type=ReferenceType.FOREIGN_KEY,
                reference_location=ReferenceLocation.DATABASE,
                file_path="models/order.py",
                line_number=10,
                confidence=0.90,
                criticality=Criticality.HIGH,
                provider="user_id",
            ),
            # Configuration
            Reference(
                reference_type=ReferenceType.ENV_VAR,
                reference_location=ReferenceLocation.CONFIGURATION,
                file_path=".env",
                line_number=1,
                confidence=0.85,
                criticality=Criticality.MEDIUM,
                provider="AUTH_SECRET_KEY",
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
        
        # Verify evidence structure
        assert evidence.target_name == "AuthService"
        assert evidence.total_references == 8
        assert evidence.overall_criticality == Criticality.CRITICAL
        assert evidence.overall_impact_score > 0.0
        
        # Verify runtime group
        assert evidence.runtime is not None
        assert evidence.runtime.reference_count == 3
        assert evidence.runtime.criticality == Criticality.CRITICAL
        assert evidence.runtime.estimated_failure_mode == FailureMode.RUNTIME_ERROR
        assert len(evidence.runtime.affected_systems) > 0
        
        # Verify database group
        assert evidence.database is not None
        assert evidence.database.reference_count == 2
        assert evidence.database.criticality == Criticality.CRITICAL
        
        # Verify critical findings
        assert len(evidence.critical_findings) > 0
        assert any("CRITICAL" in finding for finding in evidence.critical_findings)
        
        # Verify validation steps include rollback plan
        assert any("rollback" in step.lower() for step in evidence.recommended_validation_steps)

    def test_delete_unused_component(self):
        """Test DELETE of an unused component."""
        engine = EngineeringEvidenceEngine()
        
        # Simulate an unused component with minimal references
        references = [
            Reference(
                reference_type=ReferenceType.IMPORT,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="utils/deprecated.py",
                line_number=1,
                confidence=0.7,
                criticality=Criticality.LOW,
                provider="OldUtil",
            ),
        ]
        
        reference_analysis = ReferenceAnalysisResult(
            target_id=uuid4(),
            target_name="OldUtil",
            target_type="function",
            repo_id=uuid4(),
            references=references,
        )
        reference_analysis.calculate_metrics()
        
        evidence = engine.transform_references_to_evidence(reference_analysis)
        
        # Verify evidence structure
        assert evidence.target_name == "OldUtil"
        assert evidence.total_references == 1
        assert evidence.overall_criticality == Criticality.LOW
        assert evidence.overall_impact_score < 0.5
        
        # Verify no critical findings
        assert len(evidence.critical_findings) == 0 or all(
            "CRITICAL" not in finding for finding in evidence.critical_findings
        )

    def test_delete_database_table(self):
        """Test DELETE of a database table with foreign keys."""
        engine = EngineeringEvidenceEngine()
        
        references = [
            Reference(
                reference_type=ReferenceType.ORM_MODEL,
                reference_location=ReferenceLocation.DATABASE,
                file_path="models/user.py",
                line_number=5,
                confidence=0.95,
                criticality=Criticality.CRITICAL,
                provider="User",
            ),
            Reference(
                reference_type=ReferenceType.FOREIGN_KEY,
                reference_location=ReferenceLocation.DATABASE,
                file_path="models/order.py",
                line_number=10,
                confidence=0.95,
                criticality=Criticality.CRITICAL,
                provider="user_id",
            ),
            Reference(
                reference_type=ReferenceType.FOREIGN_KEY,
                reference_location=ReferenceLocation.DATABASE,
                file_path="models/payment.py",
                line_number=8,
                confidence=0.92,
                criticality=Criticality.CRITICAL,
                provider="user_id",
            ),
            Reference(
                reference_type=ReferenceType.SQL_MIGRATION,
                reference_location=ReferenceLocation.DATABASE,
                file_path="migrations/001_create_users.py",
                line_number=1,
                confidence=0.90,
                criticality=Criticality.HIGH,
                provider="create_users_table",
            ),
        ]
        
        reference_analysis = ReferenceAnalysisResult(
            target_id=uuid4(),
            target_name="User",
            target_type="model",
            repo_id=uuid4(),
            references=references,
        )
        reference_analysis.calculate_metrics()
        
        evidence = engine.transform_references_to_evidence(reference_analysis)
        
        # Verify database risk
        assert evidence.database is not None
        assert evidence.database.criticality == Criticality.CRITICAL
        assert evidence.database.estimated_failure_mode == FailureMode.DATA_CORRUPTION
        assert evidence.database_risk is not None
        assert evidence.database_risk.risk_level == Criticality.CRITICAL


class TestRenameScenario:
    """Test RENAME scenario evidence generation."""

    def test_rename_service_with_many_references(self):
        """Test RENAME of a service with many references."""
        engine = EngineeringEvidenceEngine()
        
        references = [
            # Import references (need updating)
            Reference(
                reference_type=ReferenceType.IMPORT,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="controllers/user.py",
                line_number=1,
                confidence=0.95,
                criticality=Criticality.HIGH,
                provider="AuthService",
            ),
            Reference(
                reference_type=ReferenceType.IMPORT,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="controllers/order.py",
                line_number=2,
                confidence=0.92,
                criticality=Criticality.HIGH,
                provider="AuthService",
            ),
            Reference(
                reference_type=ReferenceType.IMPORT,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="services/payment.py",
                line_number=3,
                confidence=0.88,
                criticality=Criticality.MEDIUM,
                provider="AuthService",
            ),
            # String references in configuration
            Reference(
                reference_type=ReferenceType.ENV_VAR,
                reference_location=ReferenceLocation.CONFIGURATION,
                file_path=".env",
                line_number=5,
                confidence=0.85,
                criticality=Criticality.MEDIUM,
                provider="AUTH_SERVICE_URL",
            ),
            Reference(
                reference_type=ReferenceType.YAML_CONFIG,
                reference_location=ReferenceLocation.CONFIGURATION,
                file_path="config/services.yaml",
                line_number=10,
                confidence=0.90,
                criticality=Criticality.HIGH,
                provider="auth_service",
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
        
        # Verify evidence structure
        assert evidence.target_name == "AuthService"
        assert evidence.total_references == 5
        assert evidence.overall_criticality == Criticality.HIGH
        
        # Verify configuration group has references
        assert evidence.configuration is not None
        assert evidence.configuration.reference_count == 2
        
        # Verify internal service group has imports
        assert evidence.internal_service is not None
        assert evidence.internal_service.reference_count >= 3

    def test_rename_internal_function(self):
        """Test RENAME of an internal function."""
        engine = EngineeringEvidenceEngine()
        
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="utils/helpers.py",
                line_number=10,
                confidence=0.90,
                criticality=Criticality.MEDIUM,
                provider="format_date",
                consumer="process_order",
            ),
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="utils/helpers.py",
                line_number=20,
                confidence=0.85,
                criticality=Criticality.LOW,
                provider="format_date",
                consumer="generate_report",
            ),
        ]
        
        reference_analysis = ReferenceAnalysisResult(
            target_id=uuid4(),
            target_name="format_date",
            target_type="function",
            repo_id=uuid4(),
            references=references,
        )
        reference_analysis.calculate_metrics()
        
        evidence = engine.transform_references_to_evidence(reference_analysis)
        
        # Verify evidence structure
        assert evidence.target_name == "format_date"
        assert evidence.total_references == 2
        assert evidence.overall_criticality in [Criticality.LOW, Criticality.MEDIUM]
        
        # Verify runtime group
        assert evidence.runtime is not None
        assert evidence.runtime.reference_count == 2


class TestMoveScenario:
    """Test MOVE scenario evidence generation."""

    def test_move_module_to_different_package(self):
        """Test MOVE of a module to a different package."""
        engine = EngineeringEvidenceEngine()
        
        references = [
            # Import references (need path updates)
            Reference(
                reference_type=ReferenceType.IMPORT,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="controllers/user.py",
                line_number=1,
                confidence=0.95,
                criticality=Criticality.HIGH,
                provider="auth.utils.AuthHelper",
            ),
            Reference(
                reference_type=ReferenceType.IMPORT,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="services/auth.py",
                line_number=2,
                confidence=0.92,
                criticality=Criticality.HIGH,
                provider="auth.utils.AuthHelper",
            ),
            Reference(
                reference_type=ReferenceType.IMPORT,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="tests/test_auth.py",
                line_number=3,
                confidence=0.88,
                criticality=Criticality.MEDIUM,
                provider="auth.utils.AuthHelper",
            ),
        ]
        
        reference_analysis = ReferenceAnalysisResult(
            target_id=uuid4(),
            target_name="AuthHelper",
            target_type="class",
            repo_id=uuid4(),
            references=references,
        )
        reference_analysis.calculate_metrics()
        
        evidence = engine.transform_references_to_evidence(reference_analysis)
        
        # Verify evidence structure
        assert evidence.target_name == "AuthHelper"
        assert evidence.total_references == 3
        assert evidence.overall_criticality == Criticality.HIGH
        
        # Verify imports are categorized as internal_service (since they have PascalCase)
        assert evidence.internal_service is not None
        assert evidence.internal_service.reference_count == 3

    def test_move_api_route(self):
        """Test MOVE of an API route to different endpoint."""
        engine = EngineeringEvidenceEngine()
        
        references = [
            Reference(
                reference_type=ReferenceType.FASTAPI_ROUTE,
                reference_location=ReferenceLocation.RUNTIME,
                file_path="routes/users.py",
                line_number=5,
                confidence=0.95,
                criticality=Criticality.HIGH,
                provider="/api/users/profile",
            ),
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="frontend/api.js",
                line_number=10,
                confidence=0.90,
                criticality=Criticality.HIGH,
                provider="/api/users/profile",
            ),
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="mobile/api.py",
                line_number=15,
                confidence=0.85,
                criticality=Criticality.MEDIUM,
                provider="/api/users/profile",
            ),
        ]
        
        reference_analysis = ReferenceAnalysisResult(
            target_id=uuid4(),
            target_name="/api/users/profile",
            target_type="api_route",
            repo_id=uuid4(),
            references=references,
        )
        reference_analysis.calculate_metrics()
        
        evidence = engine.transform_references_to_evidence(reference_analysis)
        
        # Verify evidence structure
        assert evidence.target_name == "/api/users/profile"
        assert evidence.total_references == 3
        
        # Verify public API group
        assert evidence.public_api is not None
        assert evidence.public_api.reference_count >= 1
        assert evidence.public_api.criticality == Criticality.HIGH


class TestEvidenceGroupingValidation:
    """Test evidence grouping and categorization."""

    def test_grouping_mixed_references(self):
        """Test grouping of mixed reference types."""
        engine = EngineeringEvidenceEngine()
        
        references = [
            # Runtime
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=10,
                confidence=0.9,
                criticality=Criticality.HIGH,
                provider="AuthService",
            ),
            # Configuration
            Reference(
                reference_type=ReferenceType.ENV_VAR,
                reference_location=ReferenceLocation.CONFIGURATION,
                file_path=".env",
                line_number=1,
                confidence=0.85,
                criticality=Criticality.MEDIUM,
                provider="DATABASE_URL",
            ),
            # Database
            Reference(
                reference_type=ReferenceType.ORM_MODEL,
                reference_location=ReferenceLocation.DATABASE,
                file_path="models.py",
                line_number=5,
                confidence=0.95,
                criticality=Criticality.CRITICAL,
                provider="User",
            ),
            # Testing
            Reference(
                reference_type=ReferenceType.PYTEST_TEST,
                reference_location=ReferenceLocation.TEST,
                file_path="test_auth.py",
                line_number=10,
                confidence=0.88,
                criticality=Criticality.LOW,
                provider="test_login",
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
        
        # Verify all groups are populated
        assert evidence.runtime is not None
        assert evidence.configuration is not None
        assert evidence.database is not None
        assert evidence.testing is not None
        
        # Verify reference counts
        assert evidence.runtime.reference_count == 1
        assert evidence.configuration.reference_count == 1
        assert evidence.database.reference_count == 1
        assert evidence.testing.reference_count == 1

    def test_confidence_validation(self):
        """Test confidence scoring validation."""
        engine = EngineeringEvidenceEngine()
        
        # High confidence references
        references = [
            Reference(
                reference_type=ReferenceType.FUNCTION_CALL,
                reference_location=ReferenceLocation.SOURCE_CODE,
                file_path="test.py",
                line_number=i,
                confidence=0.95,
                criticality=Criticality.HIGH,
                provider=f"Service{i}",
            )
            for i in range(20)
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
        
        # Verify high confidence
        assert evidence.evidence_confidence > 0.8
        assert evidence.overall_confidence > 0.8

    def test_empty_evidence_handling(self):
        """Test handling of empty evidence."""
        engine = EngineeringEvidenceEngine()
        
        reference_analysis = ReferenceAnalysisResult(
            target_id=uuid4(),
            target_name="UnusedComponent",
            target_type="function",
            repo_id=uuid4(),
            references=[],
        )
        reference_analysis.calculate_metrics()
        
        evidence = engine.transform_references_to_evidence(reference_analysis)
        
        # Verify empty evidence handling
        assert evidence.total_references == 0
        assert evidence.overall_criticality == Criticality.LOW
        assert evidence.overall_impact_score == 0.0
        assert "unused" in evidence.overall_summary.lower() or "no references" in evidence.overall_summary.lower()
