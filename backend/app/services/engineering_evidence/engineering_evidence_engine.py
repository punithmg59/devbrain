"""Engineering Evidence Engine - Unified Orchestrator."""

import logging
from uuid import UUID

from app.services.reference_intelligence.models import ReferenceAnalysisResult, Criticality
from .models import (
    EngineeringEvidence, EvidenceGroup, EvidenceCategory, 
    RiskCategory, RiskAssessment, FailureMode
)
from .grouping_logic import GroupingLogic
from .scoring_logic import ScoringLogic

logger = logging.getLogger(__name__)


class EngineeringEvidenceEngine:
    """
    Unified Engineering Evidence Engine.
    
    This engine transforms raw references from Reference Intelligence Engine
    into structured engineering evidence that explains WHY references matter.
    
    This is the single source of truth for engineering decisions.
    Consumed by:
    - Reasoning Engine
    - Simulation Engine
    - Engineering Report
    
    Never consume raw references directly - always use EngineeringEvidence.
    """
    
    def __init__(self):
        self.grouping_logic = GroupingLogic()
        self.scoring_logic = ScoringLogic()
    
    def transform_references_to_evidence(
        self,
        reference_analysis: ReferenceAnalysisResult
    ) -> EngineeringEvidence:
        """
        Transform raw references into structured engineering evidence.
        
        Args:
            reference_analysis: ReferenceAnalysisResult from Reference Intelligence Engine
            
        Returns:
            EngineeringEvidence with grouped and scored evidence
        """
        logger.info(f"Transforming {reference_analysis.total_references} references into engineering evidence")
        
        # Group references by category
        grouped_refs = self.grouping_logic.group_references(reference_analysis.references)
        
        # Create evidence groups with metrics
        evidence_groups = {}
        for category, refs in grouped_refs.items():
            if refs:  # Only create groups with references
                evidence_groups[category] = self._create_evidence_group(
                    category, refs
                )
        
        # Create engineering evidence
        evidence = EngineeringEvidence(
            target_id=reference_analysis.target_id,
            target_name=reference_analysis.target_name,
            target_type=reference_analysis.target_type,
            repo_id=reference_analysis.repo_id,
            runtime=evidence_groups.get(EvidenceCategory.RUNTIME),
            configuration=evidence_groups.get(EvidenceCategory.CONFIGURATION),
            infrastructure=evidence_groups.get(EvidenceCategory.INFRASTRUCTURE),
            database=evidence_groups.get(EvidenceCategory.DATABASE),
            testing=evidence_groups.get(EvidenceCategory.TESTING),
            public_api=evidence_groups.get(EvidenceCategory.PUBLIC_API),
            internal_service=evidence_groups.get(EvidenceCategory.INTERNAL_SERVICE),
            external_dependency=evidence_groups.get(EvidenceCategory.EXTERNAL_DEPENDENCY),
            overall_summary=self.scoring_logic.generate_overall_summary(grouped_refs),
            evidence_confidence=0.0,  # Will be calculated by calculate_overall_metrics()
        )
        
        # Calculate overall metrics
        evidence.calculate_overall_metrics()
        
        # Calculate data completeness and generate limitation statements
        evidence.calculate_data_completeness()
        evidence.generate_limitation_statements()
        
        # Generate risk assessments
        evidence.deployment_risk = self._generate_risk_assessment(
            RiskCategory.DEPLOYMENT,
            evidence_groups.get(EvidenceCategory.INFRASTRUCTURE),
            evidence_groups.get(EvidenceCategory.CONFIGURATION)
        )
        evidence.runtime_risk = self._generate_risk_assessment(
            RiskCategory.RUNTIME,
            evidence_groups.get(EvidenceCategory.RUNTIME),
            evidence_groups.get(EvidenceCategory.INTERNAL_SERVICE)
        )
        evidence.testing_risk = self._generate_risk_assessment(
            RiskCategory.TESTING,
            evidence_groups.get(EvidenceCategory.TESTING),
            None
        )
        evidence.configuration_risk = self._generate_risk_assessment(
            RiskCategory.CONFIGURATION,
            evidence_groups.get(EvidenceCategory.CONFIGURATION),
            None
        )
        evidence.database_risk = self._generate_risk_assessment(
            RiskCategory.DATABASE,
            evidence_groups.get(EvidenceCategory.DATABASE),
            None
        )
        
        # Generate critical findings
        evidence.critical_findings = self.scoring_logic.generate_critical_findings(evidence_groups)
        
        # Generate validation steps
        evidence.recommended_validation_steps = self.scoring_logic.generate_validation_steps(
            evidence_groups,
            evidence.overall_criticality
        )
        
        logger.info(f"Evidence transformation complete: {evidence.total_references} total references")
        logger.info(f"  - Overall criticality: {evidence.overall_criticality}")
        logger.info(f"  - Overall impact score: {evidence.overall_impact_score:.2f}")
        logger.info(f"  - Overall confidence: {evidence.overall_confidence:.2f}")
        logger.info(f"  - Evidence confidence: {evidence.evidence_confidence:.2f}")
        
        return evidence
    
    def _create_evidence_group(
        self,
        category: EvidenceCategory,
        references: list
    ) -> EvidenceGroup:
        """
        Create an evidence group with calculated metrics.
        
        Args:
            category: Evidence category
            references: List of references in the category
            
        Returns:
            EvidenceGroup with calculated metrics
        """
        # Calculate metrics
        criticality = self.scoring_logic.calculate_criticality(references)
        impact_score = self.scoring_logic.calculate_impact_score(references, category)
        confidence = self.scoring_logic.calculate_confidence(references)
        
        # Determine failure mode
        failure_mode = self.grouping_logic.determine_failure_mode(category, references)
        
        # Generate engineering summary
        engineering_summary = self.scoring_logic.generate_engineering_summary(
            category, references, criticality, impact_score
        )
        
        # Extract affected systems
        affected_systems = self.grouping_logic.extract_affected_systems(references)
        
        # Extract risk drivers
        risk_drivers = self.grouping_logic.extract_risk_drivers(references, category)
        
        # Create evidence group
        group = EvidenceGroup(
            category=category,
            references=references,
            criticality=criticality,
            impact_score=impact_score,
            confidence=confidence,
            engineering_summary=engineering_summary,
            estimated_failure_mode=failure_mode,
            risk_drivers=risk_drivers,
            affected_systems=affected_systems,
        )
        
        # Calculate group metrics
        group.calculate_metrics()
        
        return group
    
    def _generate_risk_assessment(
        self,
        risk_category: RiskCategory,
        primary_group: EvidenceGroup,
        secondary_group: EvidenceGroup = None
    ) -> RiskAssessment:
        """
        Generate risk assessment for a category.
        
        Args:
            risk_category: Risk category
            primary_group: Primary evidence group
            secondary_group: Secondary evidence group (optional)
            
        Returns:
            RiskAssessment object
        """
        if not primary_group:
            # Return low risk assessment if no group
            return RiskAssessment(
                category=risk_category,
                risk_level=Criticality.LOW,
                risk_score=0.0,
                affected_systems=[],
                failure_probability=0.0,
                description=f"No {risk_category.value} dependencies found."
            )
        
        # Combine affected systems from both groups
        affected_systems = list(set(primary_group.affected_systems))
        if secondary_group:
            affected_systems.extend(secondary_group.affected_systems)
            affected_systems = list(set(affected_systems))
        
        # Use primary group's failure mode
        failure_mode = primary_group.estimated_failure_mode
        
        return self.scoring_logic.generate_risk_assessment(
            category=risk_category,
            criticality=primary_group.criticality,
            impact_score=primary_group.impact_score,
            affected_systems=affected_systems,
            failure_mode=failure_mode
        )
