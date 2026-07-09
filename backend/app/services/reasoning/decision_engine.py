"""
Decision Engine (Layer 3)

Formulates the primary decision based on intent and risk level.
All decisions are grounded in repository evidence - never from LLM knowledge alone.
"""

from typing import Tuple
import logging

from app.services.intent.schemas import Intent
from app.services.engineering_evidence.models import EngineeringEvidence, Criticality
from app.services.reasoning.schemas.engineering_decision import RiskLevel, DecisionType

logger = logging.getLogger(__name__)


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
        # Ground decision in repository evidence
        reason_parts = [f"{evidence.target_name} has {evidence.total_references} references across the codebase."]
        
        # Add dependency graph evidence
        if evidence.dependency_graph and evidence.dependency_graph.total_edges > 0:
            reason_parts.append(f" Dependency graph shows {evidence.dependency_graph.total_edges} dependency edges.")
        
        # Add AST evidence
        if evidence.ast_nodes:
            reason_parts.append(f" AST analysis identified {len(evidence.ast_nodes)} related code nodes.")
        
        # Add class evidence
        if evidence.classes:
            reason_parts.append(f" {len(evidence.classes)} classes may be affected.")
        
        # Add function evidence
        if evidence.functions:
            reason_parts.append(f" {len(evidence.functions)} functions may be affected.")
        
        if evidence.runtime and evidence.runtime.criticality == Criticality.CRITICAL:
            reason_parts.append(f" Critical runtime dependencies detected: {evidence.runtime.critical_count} critical references.")
        if evidence.database:
            reason_parts.append(" Database dependencies present.")
        if evidence.public_api:
            reason_parts.append(" Public API dependencies will affect external consumers.")
        
        # Add limitations if evidence is incomplete
        if evidence.limitations:
            reason_parts.append(f" Note: {len(evidence.limitations)} data limitations detected.")
        
        reason = " ".join(reason_parts)
        
        if risk in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            return (
                DecisionType.DO_NOT_DELETE,
                f"Deleting {evidence.target_name} is highly risky.",
                reason
            )
        elif risk == RiskLevel.MEDIUM:
            return (
                DecisionType.SAFE_WITH_UPDATES,
                f"Deleting {evidence.target_name} requires careful updates.",
                reason
            )
        else:
            return (
                DecisionType.SAFE_TO_DELETE,
                f"Deleting {evidence.target_name} is safe.",
                reason
            )

    def _handle_rename(self, evidence: EngineeringEvidence, risk: RiskLevel) -> Tuple[DecisionType, str, str]:
        if risk in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            return (
                DecisionType.PROCEED_WITH_CAUTION,
                f"Renaming {evidence.target_name} will affect {evidence.total_references} references.",
                f"Due to the high number of references ({evidence.total_references}), a phased migration is recommended."
            )
        else:
            return (
                DecisionType.SAFE_WITH_UPDATES,
                f"Renaming {evidence.target_name} is safe with reference updates.",
                f"Found {evidence.total_references} references. Find and replace will cover the identified references."
            )

    def _handle_add_feature(self, evidence: EngineeringEvidence) -> Tuple[DecisionType, str, str]:
        # Try to find integration points based on evidence groups
        if evidence.internal_service and evidence.internal_service.reference_count > 0:
            top_service = evidence.internal_service.affected_systems[0] if evidence.internal_service.affected_systems else "existing module"
            return (
                DecisionType.IMPLEMENT_IN_MODULE,
                f"Add this feature within the {top_service} boundary.",
                f"{top_service} is the most architecturally appropriate service for this feature based on dependency analysis."
            )
        else:
            return (
                DecisionType.GENERATE_IMPLEMENTATION_PLAN,
                f"Create a new module for this feature.",
                f"No existing integration points perfectly match the feature requirements."
            )

    def _handle_architecture(self, evidence: EngineeringEvidence) -> Tuple[DecisionType, str, str]:
        # Ground architecture explanation in repository data
        summary = f"Architectural overview for {evidence.target_name}."
        
        reason_parts = [f"Found {evidence.total_references} references"]
        
        # Add repository structure evidence
        if evidence.classes:
            reason_parts.append(f"{len(evidence.classes)} classes")
        if evidence.functions:
            reason_parts.append(f"{len(evidence.functions)} functions")
        if evidence.api_routes:
            reason_parts.append(f"{len(evidence.api_routes)} API routes")
        if evidence.imports:
            reason_parts.append(f"{len(evidence.imports)} imports")
        
        # Add dependency graph evidence
        if evidence.dependency_graph:
            reason_parts.append(f"{evidence.dependency_graph.total_edges} dependency edges")
        
        # Add call graph evidence
        if evidence.call_graph:
            reason_parts.append(f"{len(evidence.call_graph.function_calls)} function call relationships")
        
        # Count non-empty evidence groups
        active_groups = len([g for g in [evidence.runtime, evidence.database, evidence.public_api, evidence.internal_service] if g])
        reason_parts.append(f"across {active_groups} dependency categories")
        
        # Add limitations
        if evidence.limitations:
            reason_parts.append(f"(with {len(evidence.limitations)} data limitations)")
        
        reason = ", ".join(reason_parts) + "."
        
        return (
            DecisionType.EXPLAIN_ARCHITECTURE,
            summary,
            reason
        )

    def _handle_planning(self, evidence: EngineeringEvidence) -> Tuple[DecisionType, str, str]:
        # Ground planning in repository evidence
        reason_parts = [f"Based on {evidence.total_references} references"]
        
        if evidence.dependency_graph:
            reason_parts.append(f"dependency graph with {evidence.dependency_graph.total_edges} edges")
        if evidence.classes:
            reason_parts.append(f"{len(evidence.classes)} classes")
        if evidence.functions:
            reason_parts.append(f"{len(evidence.functions)} functions")
        
        if evidence.limitations:
            reason_parts.append(f"(note: {len(evidence.limitations)} data limitations)")
        
        reason = ", ".join(reason_parts) + "."
        
        return (
            DecisionType.GENERATE_IMPLEMENTATION_PLAN,
            f"Implementation plan for {evidence.target_name}.",
            reason
        )

    def _handle_refactor(self, evidence: EngineeringEvidence, risk: RiskLevel) -> Tuple[DecisionType, str, str]:
        if risk in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            return (
                DecisionType.REFACTOR_HIGH_RISK,
                f"Refactoring {evidence.target_name} carries high risk.",
                f"It has {evidence.total_references} references with criticality: {evidence.overall_criticality}. Thorough test coverage required."
            )
        else:
            return (
                DecisionType.REFACTOR_SAFE,
                f"Refactoring {evidence.target_name} is relatively safe.",
                f"Its blast radius is contained with {evidence.total_references} references and manageable dependencies."
            )

    def _handle_dependency(self, evidence: EngineeringEvidence, risk: RiskLevel) -> Tuple[DecisionType, str, str]:
        return (
            DecisionType.RESOLVE_DEPENDENCY,
            f"Dependency analysis for {evidence.target_name}.",
            f"Identified {evidence.total_references} references across runtime, database, and API dependencies."
        )
