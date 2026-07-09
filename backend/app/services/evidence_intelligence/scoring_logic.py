"""Evidence Intelligence Engine - Scoring Logic."""

import logging
from typing import List

from app.services.reference_intelligence.models import Reference, Criticality
from .models import EvidenceCategory, EvidenceGroup, FailureMode

logger = logging.getLogger(__name__)


class ScoringLogic:
    """Calculates scores for evidence groups."""
    
    @staticmethod
    def calculate_criticality(references: List[Reference]) -> Criticality:
        """
        Calculate overall criticality for a group of references.
        
        Args:
            references: List of references
            
        Returns:
            Overall criticality level
        """
        if not references:
            return Criticality.LOW
        
        critical_count = sum(1 for r in references if r.criticality == Criticality.CRITICAL)
        high_count = sum(1 for r in references if r.criticality == Criticality.HIGH)
        
        if critical_count > 0:
            return Criticality.CRITICAL
        elif high_count > 0:
            return Criticality.HIGH
        elif len(references) > 10:
            return Criticality.MEDIUM
        else:
            return Criticality.LOW
    
    @staticmethod
    def calculate_impact_score(references: List[Reference], category: EvidenceCategory) -> float:
        """
        Calculate impact score for a group of references.
        
        Args:
            references: List of references
            category: Evidence category
            
        Returns:
            Impact score between 0.0 and 1.0
        """
        if not references:
            return 0.0
        
        # Base score from reference count
        count_score = min(len(references) / 50.0, 1.0)  # Cap at 50 references
        
        # Criticality multiplier
        criticality_multiplier = 1.0
        critical_count = sum(1 for r in references if r.criticality == Criticality.CRITICAL)
        high_count = sum(1 for r in references if r.criticality == Criticality.HIGH)
        
        if critical_count > 0:
            criticality_multiplier = 1.5
        elif high_count > 0:
            criticality_multiplier = 1.2
        
        # Category-specific adjustments
        category_multiplier = ScoringLogic._get_category_multiplier(category)
        
        # Calculate final score
        impact_score = count_score * criticality_multiplier * category_multiplier
        return min(impact_score, 1.0)
    
    @staticmethod
    def _get_category_multiplier(category: EvidenceCategory) -> float:
        """Get category-specific impact multiplier."""
        multipliers = {
            EvidenceCategory.RUNTIME_DEPENDENCIES: 1.3,  # Highest impact
            EvidenceCategory.PUBLIC_API_DEPENDENCIES: 1.2,  # High impact
            EvidenceCategory.DATABASE_DEPENDENCIES: 1.2,  # High impact
            EvidenceCategory.INFRASTRUCTURE_DEPENDENCIES: 1.1,  # Medium-high impact
            EvidenceCategory.CONFIGURATION_DEPENDENCIES: 1.0,  # Medium impact
            EvidenceCategory.INTERNAL_DEPENDENCIES: 0.9,  # Medium-low impact
            EvidenceCategory.TESTING_DEPENDENCIES: 0.7,  # Lower impact
        }
        return multipliers.get(category, 1.0)
    
    @staticmethod
    def calculate_confidence(references: List[Reference]) -> float:
        """
        Calculate confidence score for a group of references.
        
        Args:
            references: List of references
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not references:
            return 0.0
        
        # Average confidence from references
        confidences = [r.confidence for r in references]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Boost confidence if we have many references
        count_boost = min(len(references) / 20.0, 0.2)  # Max 0.2 boost
        
        final_confidence = avg_confidence + count_boost
        return min(final_confidence, 1.0)
    
    @staticmethod
    def generate_engineering_summary(
        category: EvidenceCategory,
        references: List[Reference],
        criticality: Criticality,
        impact_score: float
    ) -> str:
        """
        Generate engineering summary for an evidence group.
        
        Args:
            category: Evidence category
            references: List of references
            criticality: Overall criticality
            impact_score: Impact score
            
        Returns:
            Engineering summary string
        """
        count = len(references)
        
        if count == 0:
            return f"No {category.value.replace('_', ' ')} found."
        
        # Base summary
        summary = f"Found {count} {category.value.replace('_', ' ')}."
        
        # Add criticality context
        if criticality == Criticality.CRITICAL:
            summary += " Critical dependencies detected."
        elif criticality == Criticality.HIGH:
            summary += " High-risk dependencies detected."
        elif criticality == Criticality.MEDIUM:
            summary += " Moderate-risk dependencies detected."
        
        # Add impact context
        if impact_score > 0.8:
            summary += " High impact expected."
        elif impact_score > 0.5:
            summary += " Moderate impact expected."
        else:
            summary += " Low impact expected."
        
        # Category-specific context
        if category == EvidenceCategory.RUNTIME_DEPENDENCIES:
            summary += " These are runtime dependencies that will cause errors if modified."
        elif category == EvidenceCategory.CONFIGURATION_DEPENDENCIES:
            summary += " These are configuration dependencies that may require updates."
        elif category == EvidenceCategory.DATABASE_DEPENDENCIES:
            summary += " These are database dependencies that may require migration planning."
        elif category == EvidenceCategory.TESTING_DEPENDENCIES:
            summary += " These are test dependencies that may need updates."
        
        return summary
    
    @staticmethod
    def generate_executive_summary(evidence_groups: dict[EvidenceCategory, EvidenceGroup]) -> str:
        """
        Generate executive summary from all evidence groups.
        
        Args:
            evidence_groups: Dictionary of evidence groups
            
        Returns:
            Executive summary string
        """
        total_refs = sum(group.reference_count for group in evidence_groups.values() if group)
        
        if total_refs == 0:
            return "No references found. The target appears to be unused."
        
        # Count critical groups
        critical_groups = [
            cat for cat, group in evidence_groups.items()
            if group and group.criticality == Criticality.CRITICAL
        ]
        
        # Build summary
        summary = f"Found {total_refs} total references across the codebase."
        
        if critical_groups:
            group_names = [cat.value.replace('_', ' ') for cat in critical_groups]
            summary += f" Critical dependencies in: {', '.join(group_names)}."
        else:
            summary += " No critical dependencies detected."
        
        return summary
    
    @staticmethod
    def generate_risk_assessment(
        overall_criticality: Criticality,
        overall_impact_score: float,
        evidence_groups: dict[EvidenceCategory, EvidenceGroup]
    ) -> str:
        """
        Generate risk assessment.
        
        Args:
            overall_criticality: Overall criticality
            overall_impact_score: Overall impact score
            evidence_groups: Dictionary of evidence groups
            
        Returns:
            Risk assessment string
        """
        if overall_criticality == Criticality.CRITICAL:
            return "CRITICAL: Modifying this target will cause system-wide failures. Proceed only with comprehensive testing and rollback plan."
        elif overall_criticality == Criticality.HIGH:
            return "HIGH: Modifying this target will cause significant impact. Thorough testing and migration planning required."
        elif overall_criticality == Criticality.MEDIUM:
            return "MODERATE: Modifying this target will cause moderate impact. Testing and validation recommended."
        else:
            return "LOW: Modifying this target will cause minimal impact. Standard testing procedures sufficient."
    
    @staticmethod
    def generate_recommended_actions(
        evidence_groups: dict[EvidenceCategory, EvidenceGroup],
        overall_criticality: Criticality
    ) -> List[str]:
        """
        Generate recommended actions based on evidence.
        
        Args:
            evidence_groups: Dictionary of evidence groups
            overall_criticality: Overall criticality
            
        Returns:
            List of recommended actions
        """
        actions = []
        
        # Critical actions
        if overall_criticality == Criticality.CRITICAL:
            actions.append("Create comprehensive rollback plan before modification")
            actions.append("Implement feature flag for gradual rollout")
            actions.append("Prepare hotfix deployment strategy")
        
        # High actions
        elif overall_criticality == Criticality.HIGH:
            actions.append("Create migration plan for dependent components")
            actions.append("Schedule maintenance window for deployment")
            actions.append("Prepare monitoring and alerting")
        
        # Moderate actions
        elif overall_criticality == Criticality.MEDIUM:
            actions.append("Run full test suite before and after modification")
            actions.append("Update affected tests")
            actions.append("Review and update documentation")
        
        # Low actions
        else:
            actions.append("Run relevant tests")
            actions.append("Update documentation if needed")
        
        # Category-specific actions
        for category, group in evidence_groups.items():
            if not group or group.reference_count == 0:
                continue
            
            if category == EvidenceCategory.RUNTIME_DEPENDENCIES:
                actions.append("Review runtime dependency chain for cascade effects")
            elif category == EvidenceCategory.CONFIGURATION_DEPENDENCIES:
                actions.append("Update configuration files with new references")
            elif category == EvidenceCategory.DATABASE_DEPENDENCIES:
                actions.append("Plan database migration for schema changes")
            elif category == EvidenceCategory.INFRASTRUCTURE_DEPENDENCIES:
                actions.append("Update infrastructure configuration")
            elif category == EvidenceCategory.TESTING_DEPENDENCIES:
                actions.append("Update test cases to reflect changes")
        
        return actions
