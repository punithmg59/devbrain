"""Engineering Evidence Engine - Scoring Logic."""

import logging
from typing import List

from app.services.reference_intelligence.models import Reference, Criticality
from .models import EvidenceCategory, RiskCategory, RiskAssessment, FailureMode

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
            EvidenceCategory.RUNTIME: 1.3,  # Highest impact
            EvidenceCategory.PUBLIC_API: 1.2,  # High impact
            EvidenceCategory.DATABASE: 1.2,  # High impact
            EvidenceCategory.INFRASTRUCTURE: 1.1,  # Medium-high impact
            EvidenceCategory.CONFIGURATION: 1.0,  # Medium impact
            EvidenceCategory.INTERNAL_SERVICE: 0.9,  # Medium-low impact
            EvidenceCategory.TESTING: 0.7,  # Lower impact
            EvidenceCategory.EXTERNAL_DEPENDENCY: 0.8,  # Lower-medium impact
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
            return f"No {category.value.replace('_', ' ')} dependencies found."
        
        # Base summary
        category_name = category.value.replace('_', ' ').title()
        summary = f"Found {count} {category_name.lower()} dependencies."
        
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
        if category == EvidenceCategory.RUNTIME:
            summary += " These are runtime dependencies that will cause errors if modified."
        elif category == EvidenceCategory.CONFIGURATION:
            summary += " These are configuration dependencies that may require updates."
        elif category == EvidenceCategory.DATABASE:
            summary += " These are database dependencies that may require migration planning."
        elif category == EvidenceCategory.TESTING:
            summary += " These are test dependencies that may need updates."
        elif category == EvidenceCategory.PUBLIC_API:
            summary += " These are public API dependencies that affect external consumers."
        elif category == EvidenceCategory.INFRASTRUCTURE:
            summary += " These are infrastructure dependencies that affect deployment."
        elif category == EvidenceCategory.INTERNAL_SERVICE:
            summary += " These are internal service dependencies that may cause cascade failures."
        
        return summary
    
    @staticmethod
    def generate_overall_summary(evidence_groups: dict[EvidenceCategory, List[Reference]]) -> str:
        """
        Generate overall summary from all evidence groups.
        
        Args:
            evidence_groups: Dictionary of evidence groups
            
        Returns:
            Overall summary string
        """
        total_refs = sum(len(refs) for refs in evidence_groups.values())
        
        if total_refs == 0:
            return "No references found. The target appears to be unused."
        
        # Count groups with references
        populated_groups = [cat for cat, refs in evidence_groups.items() if refs]
        
        # Count critical references
        critical_count = sum(
            1 for refs in evidence_groups.values()
            for ref in refs
            if ref.criticality == Criticality.CRITICAL
        )
        
        # Build summary
        summary = f"Found {total_refs} total references across {len(populated_groups)} dependency categories."
        
        if critical_count > 0:
            summary += f" {critical_count} critical dependencies detected."
        
        # Add context about affected areas
        if EvidenceCategory.RUNTIME in populated_groups:
            summary += " Runtime dependencies present."
        if EvidenceCategory.DATABASE in populated_groups:
            summary += " Database dependencies present."
        if EvidenceCategory.PUBLIC_API in populated_groups:
            summary += " Public API dependencies present."
        
        return summary
    
    @staticmethod
    def generate_risk_assessment(
        category: RiskCategory,
        criticality: Criticality,
        impact_score: float,
        affected_systems: List[str],
        failure_mode: FailureMode
    ) -> RiskAssessment:
        """
        Generate risk assessment for a specific category.
        
        Args:
            category: Risk category
            criticality: Criticality level
            impact_score: Impact score
            affected_systems: List of affected systems
            failure_mode: Estimated failure mode
            
        Returns:
            RiskAssessment object
        """
        # Calculate risk score based on criticality and impact
        risk_score = impact_score
        if criticality == Criticality.CRITICAL:
            risk_score = min(risk_score * 1.5, 1.0)
        elif criticality == Criticality.HIGH:
            risk_score = min(risk_score * 1.2, 1.0)
        
        # Calculate failure probability
        failure_probability = risk_score * 0.8  # Conservative estimate
        
        # Generate description
        description = ScoringLogic._generate_risk_description(
            category, criticality, failure_mode, len(affected_systems)
        )
        
        return RiskAssessment(
            category=category,
            risk_level=criticality,
            risk_score=risk_score,
            affected_systems=affected_systems,
            failure_probability=failure_probability,
            description=description
        )
    
    @staticmethod
    def _generate_risk_description(
        category: RiskCategory,
        criticality: Criticality,
        failure_mode: FailureMode,
        system_count: int
    ) -> str:
        """Generate risk description."""
        base = f"{category.value.title()} risk: "
        
        if criticality == Criticality.CRITICAL:
            base += "Critical. "
        elif criticality == Criticality.HIGH:
            base += "High. "
        elif criticality == Criticality.MEDIUM:
            base += "Moderate. "
        else:
            base += "Low. "
        
        if system_count > 0:
            base += f"Affects {system_count} system(s). "
        
        base += f"Expected failure mode: {failure_mode.value.replace('_', ' ')}."
        
        return base
    
    @staticmethod
    def generate_critical_findings(evidence_groups: dict) -> List[str]:
        """
        Generate critical findings from evidence groups.
        
        Args:
            evidence_groups: Dictionary of evidence groups
            
        Returns:
            List of critical finding descriptions
        """
        findings = []
        
        for category, group in evidence_groups.items():
            if not group:
                continue
            
            if group.criticality == Criticality.CRITICAL:
                findings.append(
                    f"CRITICAL: {category.value.replace('_', ' ').title()} dependencies "
                    f"contain {group.critical_count} critical references that will cause system failures"
                )
            elif group.criticality == Criticality.HIGH:
                findings.append(
                    f"HIGH: {category.value.replace('_', ' ').title()} dependencies "
                    f"contain {group.high_count} high-risk references with significant impact"
                )
        
        return findings
    
    @staticmethod
    def generate_validation_steps(
        evidence_groups: dict,
        overall_criticality: Criticality
    ) -> List[str]:
        """
        Generate recommended validation steps.
        
        Args:
            evidence_groups: Dictionary of evidence groups
            overall_criticality: Overall criticality
            
        Returns:
            List of validation steps
        """
        steps = []
        
        # Critical steps
        if overall_criticality == Criticality.CRITICAL:
            steps.append("Create comprehensive rollback plan before modification")
            steps.append("Implement feature flag for gradual rollout")
            steps.append("Prepare hotfix deployment strategy")
            steps.append("Run full integration test suite")
            steps.append("Perform load testing with expected traffic")
        
        # High steps
        elif overall_criticality == Criticality.HIGH:
            steps.append("Create migration plan for dependent components")
            steps.append("Schedule maintenance window for deployment")
            steps.append("Prepare monitoring and alerting")
            steps.append("Run integration tests for affected systems")
            steps.append("Perform smoke testing in staging environment")
        
        # Moderate steps
        elif overall_criticality == Criticality.MEDIUM:
            steps.append("Run full test suite before and after modification")
            steps.append("Update affected tests")
            steps.append("Review and update documentation")
            steps.append("Perform regression testing")
        
        # Low steps
        else:
            steps.append("Run relevant unit tests")
            steps.append("Update documentation if needed")
            steps.append("Perform basic smoke testing")
        
        # Category-specific steps
        for category, group in evidence_groups.items():
            if not group or group.reference_count == 0:
                continue
            
            if category == EvidenceCategory.RUNTIME:
                steps.append("Validate runtime dependency chain for cascade effects")
            elif category == EvidenceCategory.CONFIGURATION:
                steps.append("Update configuration files with new references")
                steps.append("Validate configuration in all environments")
            elif category == EvidenceCategory.DATABASE:
                steps.append("Plan database migration for schema changes")
                steps.append("Backup database before migration")
                steps.append("Validate data integrity after migration")
            elif category == EvidenceCategory.INFRASTRUCTURE:
                steps.append("Update infrastructure configuration")
                steps.append("Validate deployment pipeline")
            elif category == EvidenceCategory.TESTING:
                steps.append("Update test cases to reflect changes")
                steps.append("Ensure test coverage remains adequate")
            elif category == EvidenceCategory.PUBLIC_API:
                steps.append("Notify external API consumers of changes")
                steps.append("Provide API version compatibility")
        
        return steps
