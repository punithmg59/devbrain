"""Evidence Intelligence Engine - Unified Orchestrator."""

import logging
from uuid import UUID

from app.services.reference_intelligence.models import ReferenceAnalysisResult
from .models import EngineeringEvidence, EvidenceGroup, EvidenceCategory
from .grouping_logic import GroupingLogic
from .scoring_logic import ScoringLogic

logger = logging.getLogger(__name__)


class EvidenceIntelligenceEngine:
    """
    Unified Evidence Intelligence Engine.
    
    This engine transforms raw references from Reference Intelligence Engine
    into structured engineering evidence that can be consumed by:
    - Reasoning Engine
    - Simulation Engine
    - Engineering Report
    
    This is the single source of truth for engineering evidence.
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
        logger.info(f"Transforming {reference_analysis.total_references} references into evidence")
        
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
            runtime_dependencies=evidence_groups.get(EvidenceCategory.RUNTIME_DEPENDENCIES),
            configuration_dependencies=evidence_groups.get(EvidenceCategory.CONFIGURATION_DEPENDENCIES),
            infrastructure_dependencies=evidence_groups.get(EvidenceCategory.INFRASTRUCTURE_DEPENDENCIES),
            database_dependencies=evidence_groups.get(EvidenceCategory.DATABASE_DEPENDENCIES),
            testing_dependencies=evidence_groups.get(EvidenceCategory.TESTING_DEPENDENCIES),
            public_api_dependencies=evidence_groups.get(EvidenceCategory.PUBLIC_API_DEPENDENCIES),
            internal_dependencies=evidence_groups.get(EvidenceCategory.INTERNAL_DEPENDENCIES),
        )
        
        # Calculate overall metrics
        evidence.calculate_overall_metrics()
        
        # Generate summaries
        evidence.executive_summary = self.scoring_logic.generate_executive_summary(evidence_groups)
        evidence.risk_assessment = self.scoring_logic.generate_risk_assessment(
            evidence.overall_criticality,
            evidence.overall_impact_score,
            evidence_groups
        )
        evidence.recommended_actions = self.scoring_logic.generate_recommended_actions(
            evidence_groups,
            evidence.overall_criticality
        )
        
        logger.info(f"Evidence transformation complete: {evidence.total_references} total references")
        logger.info(f"  - Overall criticality: {evidence.overall_criticality}")
        logger.info(f"  - Overall impact score: {evidence.overall_impact_score:.2f}")
        logger.info(f"  - Overall confidence: {evidence.overall_confidence:.2f}")
        
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
        
        # Create evidence group
        group = EvidenceGroup(
            category=category,
            references=references,
            criticality=criticality,
            impact_score=impact_score,
            confidence=confidence,
            engineering_summary=engineering_summary,
            estimated_failure_mode=failure_mode,
        )
        
        # Calculate group metrics
        group.calculate_metrics()
        
        return group
