"""
Reasoning Engine Orchestrator (Layer 3)

The brain of DevBrain. Connects structured evidence to engineering decisions.
"""

import logging
from typing import Dict, Any, List

from app.services.intent.schemas import Intent
from app.services.repository_intelligence.schemas import EngineeringEvidence
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.reasoning.risk_engine import RiskEngine
from app.services.reasoning.decision_engine import DecisionEngine
from app.services.reasoning.recommendation_engine import RecommendationEngine
from app.services.reasoning.followup_engine import FollowupEngine


logger = logging.getLogger(__name__)


class ReasoningEngine:
    """
    Top-level orchestrator for Layer 3.
    Extracts decisions, recommendations, and follow-ups from structured evidence.
    """

    def __init__(self):
        self.risk_engine = RiskEngine()
        self.decision_engine = DecisionEngine()
        self.recommendation_engine = RecommendationEngine()
        self.followup_engine = FollowupEngine()

    def reason(self, intent: Intent, evidence: EngineeringEvidence) -> EngineeringDecision:
        """
        Execute the reasoning pipeline.
        
        Args:
            intent: The classified Intent from Layer 1
            evidence: The structured evidence from Layer 2
            
        Returns:
            EngineeringDecision object
        """
        logger.info(f"Reasoning over intent={intent.intent} for target={intent.target_name}")

        # 1. Evaluate Risk
        risk_level, risk_score = self.risk_engine.assess_risk(intent, evidence)

        # 2. Generate Primary Decision
        decision_type, summary, primary_reason = self.decision_engine.generate_decision(
            intent, evidence, risk_level
        )

        # 3. Generate Recommendations
        recommended_actions, required_tests, alternative_options = (
            self.recommendation_engine.generate_recommendations(intent, evidence, decision_type)
        )

        # 4. Generate Follow-up Questions
        follow_up_questions = self.followup_engine.generate_questions(intent, decision_type)

        # 5. Extract affected components for UI
        affected_components = self._extract_affected_components(evidence)

        # 6. Calculate combined confidence
        # Simple heuristic: Combine intent confidence and evidence confidence
        evidence_confidence = evidence.score.overall_confidence
        combined_confidence = round((intent.confidence * 0.4) + (evidence_confidence * 0.6), 2)

        decision = EngineeringDecision(
            decision=decision_type,
            risk_level=risk_level,
            risk_score=risk_score,
            confidence=combined_confidence,
            summary=summary,
            primary_reason=primary_reason,
            affected_components=affected_components,
            recommended_actions=recommended_actions,
            alternative_options=alternative_options,
            required_tests=required_tests,
            follow_up_questions=follow_up_questions,
        )
        
        logger.info(f"Generated decision: {decision_type} with risk {risk_level} ({risk_score})")

        return decision

    def _extract_affected_components(self, evidence: EngineeringEvidence) -> List[Dict[str, Any]]:
        """Extract a simplified list of affected components for the decision payload."""
        components = []
        
        # We only take the top 10 most relevant items to keep the payload clean
        all_items = []
        for cat, items in evidence.evidence.items.items():
            all_items.extend(items)
            
        # Sort by relevance
        all_items.sort(key=lambda x: x.relevance_score, reverse=True)
        
        for item in all_items[:10]:
            components.append({
                "name": item.name,
                "type": item.node_type,
                "category": item.category.value if hasattr(item.category, 'value') else str(item.category)
            })
            
        return components
