"""
Risk Engine (Layer 3)

Deterministically calculates risk from structured evidence without using LLMs.
All risk assessment is grounded in repository data - never from LLM knowledge alone.
"""

from typing import Tuple
import logging

from app.services.intent.schemas import Intent
from app.services.engineering_evidence.models import EngineeringEvidence, Criticality
from app.services.reasoning.schemas.engineering_decision import RiskLevel

logger = logging.getLogger(__name__)


class RiskEngine:
    """Calculates risk levels and scores from engineering evidence."""

    def assess_risk(self, intent: Intent, evidence: EngineeringEvidence) -> Tuple[RiskLevel, int]:
        """
        Assess risk purely based on the structured evidence.
        
        All risk assessment is grounded in repository data:
        - AST nodes
        - Dependency graph
        - Call graph
        - Classes and functions
        - API routes
        - Imports
        
        Args:
            intent: The original classified Intent
            evidence: The EngineeringEvidence collection
            
        Returns:
            Tuple of (RiskLevel, risk_score 0-100)
        """
        score = 0

        # 1. Evaluate Runtime Dependencies
        if evidence.runtime:
            runtime_count = evidence.runtime.reference_count
            if runtime_count > 20:
                score += 40
            elif runtime_count > 10:
                score += 25
            elif runtime_count > 0:
                score += 10
            
            # Critical runtime dependencies
            if evidence.runtime.criticality == Criticality.CRITICAL:
                score += 15

        # 2. Evaluate Database Impact
        if evidence.database:
            score += 25
            if evidence.database.criticality == Criticality.CRITICAL:
                score += 15

        # 3. Evaluate Public API Impact
        if evidence.public_api:
            score += 20
            if evidence.public_api.criticality == Criticality.CRITICAL:
                score += 15

        # 4. Evaluate Infrastructure Impact
        if evidence.infrastructure:
            score += 15

        # 5. Evaluate Configuration Impact
        if evidence.configuration:
            score += 10

        # 6. Evaluate Testing Coverage
        if evidence.testing:
            # Having tests reduces risk
            score -= 10
        else:
            # No tests increases risk if there are dependencies
            if evidence.total_references > 0:
                score += 15

        # 7. Evaluate Overall Criticality
        if evidence.overall_criticality == Criticality.CRITICAL:
            score += 20
        elif evidence.overall_criticality == Criticality.HIGH:
            score += 10

        # 8. Evaluate Architectural Centrality
        # Check if the target is a core service
        if evidence.target_type.lower() == "service":
            score += 15

        # 9. Evaluate Impact Score
        if evidence.overall_impact_score > 0.8:
            score += 15
        elif evidence.overall_impact_score > 0.5:
            score += 10

        # 10. Evaluate Repository Structure Data (NEW - grounded in actual code)
        # Dependency graph complexity
        if evidence.dependency_graph:
            if evidence.dependency_graph.total_edges > 50:
                score += 20
            elif evidence.dependency_graph.total_edges > 20:
                score += 10
            elif evidence.dependency_graph.total_edges > 5:
                score += 5
        
        # Call graph complexity
        if evidence.call_graph and len(evidence.call_graph.function_calls) > 20:
            score += 10
        
        # Class complexity
        if len(evidence.classes) > 10:
            score += 5
        
        # Function complexity
        if len(evidence.functions) > 50:
            score += 10
        elif len(evidence.functions) > 20:
            score += 5
        
        # API surface area
        if len(evidence.api_routes) > 10:
            score += 10
        elif len(evidence.api_routes) > 5:
            score += 5

        # 11. Adjust for Data Completeness (NEW - penalize incomplete evidence)
        if evidence.data_completeness:
            avg_completeness = sum(evidence.data_completeness.values()) / len(evidence.data_completeness)
            if avg_completeness < 0.5:
                # Low data completeness - increase risk due to uncertainty
                score += 15
                logger.warning(f"Low data completeness ({avg_completeness:.2f}) for {evidence.target_name}")
        
        # 12. Adjust for Evidence Confidence
        if evidence.evidence_confidence < 0.5:
            # Low confidence - increase risk due to uncertainty
            score += 10
            logger.warning(f"Low evidence confidence ({evidence.evidence_confidence:.2f}) for {evidence.target_name}")

        # Cap score at 100 and ensure minimum of 0
        score = max(0, min(score, 100))

        # Map to Risk Level
        if score >= 80:
            return RiskLevel.CRITICAL, score
        elif score >= 50:
            return RiskLevel.HIGH, score
        elif score >= 25:
            return RiskLevel.MEDIUM, score
        else:
            return RiskLevel.LOW, score
