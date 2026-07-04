"""
Risk Engine (Layer 3)

Deterministically calculates risk from structured evidence without using LLMs.
"""

from typing import Tuple

from app.services.intent.schemas import Intent
from app.services.repository_intelligence.schemas import EngineeringEvidence, EvidenceCategory
from app.services.reasoning.schemas.engineering_decision import RiskLevel


class RiskEngine:
    """Calculates risk levels and scores from engineering evidence."""

    def assess_risk(self, intent: Intent, evidence: EngineeringEvidence) -> Tuple[RiskLevel, int]:
        """
        Assess risk purely based on the structured evidence.
        
        Args:
            intent: The original classified Intent
            evidence: The EngineeringEvidence collection
            
        Returns:
            Tuple of (RiskLevel, risk_score 0-100)
        """
        score = 0

        # 1. Evaluate Callers & Dependents
        caller_count = len(evidence.evidence.get(EvidenceCategory.CALLER))
        dependent_count = len(evidence.evidence.get(EvidenceCategory.DEPENDENT))
        total_incoming = caller_count + dependent_count

        if total_incoming > 20:
            score += 40
        elif total_incoming > 10:
            score += 25
        elif total_incoming > 0:
            score += 10

        # 2. Evaluate Database Impact
        if evidence.has_database:
            score += 25

        # 3. Evaluate Workflows Affected
        if evidence.has_workflows:
            # Check for critical workflows
            critical_workflows = [w for w in evidence.evidence.workflows if w.criticality.lower() == "high"]
            if critical_workflows:
                score += 35
            else:
                score += 20

        # 4. Evaluate APIs Affected
        if evidence.has_apis:
            score += 20

        # 5. Evaluate Architectural Centrality
        # Check if the target is a core service
        if evidence.target_type.lower() == "service":
            score += 15

        # 6. Penalize for missing tests
        # If there are no tests for the target, it's riskier
        if not evidence.has_tests and total_incoming > 0:
            score += 15

        # Cap score at 100
        score = min(score, 100)

        # Map to Risk Level
        if score >= 80:
            return RiskLevel.CRITICAL, score
        elif score >= 50:
            return RiskLevel.HIGH, score
        elif score >= 25:
            return RiskLevel.MEDIUM, score
        else:
            return RiskLevel.LOW, score
