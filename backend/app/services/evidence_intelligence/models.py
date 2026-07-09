"""Evidence Intelligence Engine - Data Models."""

from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.services.reference_intelligence.models import Reference, Criticality


class EvidenceCategory(str, Enum):
    """Category of engineering evidence."""
    RUNTIME_DEPENDENCIES = "runtime_dependencies"
    CONFIGURATION_DEPENDENCIES = "configuration_dependencies"
    INFRASTRUCTURE_DEPENDENCIES = "infrastructure_dependencies"
    DATABASE_DEPENDENCIES = "database_dependencies"
    TESTING_DEPENDENCIES = "testing_dependencies"
    PUBLIC_API_DEPENDENCIES = "public_api_dependencies"
    INTERNAL_DEPENDENCIES = "internal_dependencies"


class FailureMode(str, Enum):
    """Estimated failure mode if the target is modified."""
    RUNTIME_ERROR = "runtime_error"
    BUILD_ERROR = "build_error"
    CONFIGURATION_ERROR = "configuration_error"
    DEPLOYMENT_ERROR = "deployment_error"
    TEST_FAILURE = "test_failure"
    DATA_CORRUPTION = "data_corruption"
    SERVICE_UNAVAILABLE = "service_unavailable"
    API_FAILURE = "api_failure"
    UNKNOWN = "unknown"


class EvidenceGroup(BaseModel):
    """A group of references with calculated metrics."""
    category: EvidenceCategory
    references: List[Reference] = Field(default_factory=list)
    
    # Calculated metrics
    criticality: Criticality
    impact_score: float = Field(ge=0.0, le=1.0, description="Impact score 0-1")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    
    # Engineering summary
    engineering_summary: str
    highest_risk_references: List[Reference] = Field(default_factory=list)
    estimated_failure_mode: FailureMode
    
    # Additional metrics
    reference_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    def calculate_metrics(self) -> None:
        """Calculate metrics from references."""
        self.reference_count = len(self.references)
        
        for ref in self.references:
            if ref.criticality == Criticality.CRITICAL:
                self.critical_count += 1
            elif ref.criticality == Criticality.HIGH:
                self.high_count += 1
            elif ref.criticality == Criticality.MEDIUM:
                self.medium_count += 1
            elif ref.criticality == Criticality.LOW:
                self.low_count += 1
        
        # Sort references by criticality for highest risk
        self.references.sort(
            key=lambda r: (
                0 if r.criticality == Criticality.CRITICAL else
                1 if r.criticality == Criticality.HIGH else
                2 if r.criticality == Criticality.MEDIUM else
                3
            )
        )
        self.highest_risk_references = self.references[:5]  # Top 5 highest risk


class EngineeringEvidence(BaseModel):
    """Structured engineering evidence derived from raw references."""
    target_id: UUID
    target_name: str
    target_type: str
    repo_id: UUID
    
    # Evidence groups
    runtime_dependencies: Optional[EvidenceGroup] = None
    configuration_dependencies: Optional[EvidenceGroup] = None
    infrastructure_dependencies: Optional[EvidenceGroup] = None
    database_dependencies: Optional[EvidenceGroup] = None
    testing_dependencies: Optional[EvidenceGroup] = None
    public_api_dependencies: Optional[EvidenceGroup] = None
    internal_dependencies: Optional[EvidenceGroup] = None
    
    # Overall metrics
    total_references: int = 0
    overall_criticality: Criticality = Criticality.LOW
    overall_impact_score: float = 0.0
    overall_confidence: float = 0.0
    
    # Engineering summary
    executive_summary: str
    risk_assessment: str
    recommended_actions: List[str] = Field(default_factory=list)
    
    # Failure prediction
    estimated_failure_modes: List[FailureMode] = Field(default_factory=list)
    
    def calculate_overall_metrics(self) -> None:
        """Calculate overall metrics from evidence groups."""
        groups = [
            self.runtime_dependencies,
            self.configuration_dependencies,
            self.infrastructure_dependencies,
            self.database_dependencies,
            self.testing_dependencies,
            self.public_api_dependencies,
            self.internal_dependencies,
        ]
        
        # Count total references
        self.total_references = sum(
            group.reference_count for group in groups if group
        )
        
        # Calculate overall criticality
        critical_count = sum(
            group.critical_count for group in groups if group
        )
        high_count = sum(
            group.high_count for group in groups if group
        )
        
        if critical_count > 0:
            self.overall_criticality = Criticality.CRITICAL
        elif high_count > 0:
            self.overall_criticality = Criticality.HIGH
        else:
            self.overall_criticality = Criticality.MEDIUM
        
        # Calculate overall impact score
        impact_scores = [
            group.impact_score for group in groups if group
        ]
        if impact_scores:
            self.overall_impact_score = sum(impact_scores) / len(impact_scores)
        
        # Calculate overall confidence
        confidence_scores = [
            group.confidence for group in groups if group
        ]
        if confidence_scores:
            self.overall_confidence = sum(confidence_scores) / len(confidence_scores)
        
        # Collect failure modes
        self.estimated_failure_modes = [
            group.estimated_failure_mode for group in groups if group
        ]
