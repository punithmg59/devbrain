"""
Decision Engine (Layer 3)

Formulates the primary decision based on intent and risk level.
"""

from typing import Tuple

from app.services.intent.schemas import Intent
from app.services.repository_intelligence.schemas import EngineeringEvidence, EvidenceCategory
from app.services.reasoning.schemas.engineering_decision import RiskLevel, DecisionType


class DecisionEngine:
    """Generates the primary decision enum and reasoning text."""

    def generate_decision(
        self, intent: Intent, evidence: EngineeringEvidence, risk: RiskLevel
    ) -> Tuple[DecisionType, str, str]:
        """
        Produce a decision based on intent type and risk.
        
        Returns:
            Tuple of (DecisionType, summary, primary_reason)
        """
        intent_val = intent.intent.value if hasattr(intent.intent, 'value') else str(intent.intent).upper()
        
        if intent_val == "DELETE":
            return self._handle_delete(evidence, risk)
        elif intent_val == "RENAME":
            return self._handle_rename(evidence, risk)
        elif intent_val == "ADD_FEATURE":
            return self._handle_add_feature(evidence)
        elif intent_val in ["ARCHITECTURE", "EXPLAIN"]:
            return self._handle_architecture(evidence)
        elif intent_val == "PLANNING":
            return self._handle_planning(evidence)
        elif intent_val == "REFACTOR":
            return self._handle_refactor(evidence, risk)
        elif intent_val == "DEPENDENCY":
            return self._handle_dependency(evidence, risk)
        else:
            return (
                DecisionType.UNKNOWN,
                "Unable to form a deterministic decision.",
                "Intent type is unknown or unsupported."
            )

    def _handle_delete(self, evidence: EngineeringEvidence, risk: RiskLevel) -> Tuple[DecisionType, str, str]:
        if risk in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            return (
                DecisionType.DO_NOT_DELETE,
                f"Deleting {evidence.target_name} is highly risky.",
                f"It is actively depended on by other components and removing it will cause cascading failures."
            )
        elif risk == RiskLevel.MEDIUM:
            return (
                DecisionType.SAFE_WITH_UPDATES,
                f"Deleting {evidence.target_name} requires careful updates.",
                f"There are a few dependencies that must be migrated before deletion."
            )
        else:
            return (
                DecisionType.SAFE_TO_DELETE,
                f"Deleting {evidence.target_name} is safe.",
                f"No critical dependencies or callers were found."
            )

    def _handle_rename(self, evidence: EngineeringEvidence, risk: RiskLevel) -> Tuple[DecisionType, str, str]:
        if risk in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            return (
                DecisionType.PROCEED_WITH_CAUTION,
                f"Renaming {evidence.target_name} will affect many areas.",
                f"Due to the high number of references, a phased migration is recommended over a direct rename."
            )
        else:
            return (
                DecisionType.SAFE_WITH_UPDATES,
                f"Renaming {evidence.target_name} is safe with reference updates.",
                f"Find and replace will cover the identified references."
            )

    def _handle_add_feature(self, evidence: EngineeringEvidence) -> Tuple[DecisionType, str, str]:
        # Try to find an integration point or pattern
        integration_points = evidence.evidence.get(EvidenceCategory.INTEGRATION_POINT)
        if integration_points:
            top_module = integration_points[0].name
            return (
                DecisionType.IMPLEMENT_IN_MODULE,
                f"Add this feature within the {top_module} boundary.",
                f"{top_module} is the most architecturally appropriate service for this feature."
            )
        else:
            return (
                DecisionType.GENERATE_IMPLEMENTATION_PLAN,
                f"Create a new module for this feature.",
                f"No existing integration points perfectly match the feature requirements."
            )

    def _handle_architecture(self, evidence: EngineeringEvidence) -> Tuple[DecisionType, str, str]:
        return (
            DecisionType.EXPLAIN_ARCHITECTURE,
            f"Architectural overview for {evidence.target_name}.",
            f"Generated based on the graph neighborhood of the target."
        )

    def _handle_planning(self, evidence: EngineeringEvidence) -> Tuple[DecisionType, str, str]:
        return (
            DecisionType.GENERATE_IMPLEMENTATION_PLAN,
            f"Implementation plan for {evidence.target_name}.",
            f"Based on existing patterns and integration points found in the codebase."
        )

    def _handle_refactor(self, evidence: EngineeringEvidence, risk: RiskLevel) -> Tuple[DecisionType, str, str]:
        if risk in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            return (
                DecisionType.REFACTOR_HIGH_RISK,
                f"Refactoring {evidence.target_name} carries high risk.",
                f"It is a highly central component. Thorough test coverage is required before proceeding."
            )
        else:
            return (
                DecisionType.REFACTOR_SAFE,
                f"Refactoring {evidence.target_name} is relatively safe.",
                f"Its blast radius is contained and dependencies are manageable."
            )

    def _handle_dependency(self, evidence: EngineeringEvidence, risk: RiskLevel) -> Tuple[DecisionType, str, str]:
        return (
            DecisionType.RESOLVE_DEPENDENCY,
            f"Dependency analysis for {evidence.target_name}.",
            f"Identified upstream dependents and downstream dependencies."
        )
