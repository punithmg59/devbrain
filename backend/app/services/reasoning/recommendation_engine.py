"""
Recommendation Engine (Layer 3)

Generates deterministic recommendations, required tests, and alternative options based on evidence.
"""

from typing import Tuple, List, Dict, Any

from app.services.intent.schemas import Intent
from app.services.repository_intelligence.schemas import EngineeringEvidence, EvidenceCategory
from app.services.reasoning.schemas.engineering_decision import DecisionType


class RecommendationEngine:
    """Generates actions, tests, and alternatives."""

    def generate_recommendations(
        self, intent: Intent, evidence: EngineeringEvidence, decision: DecisionType
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Generate recommendations deterministically.
        
        Returns:
            Tuple of (recommended_actions, required_tests, alternative_options)
        """
        actions = []
        tests = []
        alternatives = []

        intent_val = intent.intent.value if hasattr(intent.intent, 'value') else str(intent.intent).upper()
        
        # 1. Base intent-specific recommendations
        if intent_val == "DELETE":
            if decision == DecisionType.DO_NOT_DELETE:
                alternatives.append("Deprecate the component instead of deleting it.")
                alternatives.append("Isolate the component into a separate microservice/module.")
                actions.append("Review dependent services and assess migration effort.")
            else:
                actions.append("Remove the component from the codebase.")
                if evidence.has_callers or evidence.evidence.get(EvidenceCategory.DEPENDENT):
                    actions.append("Replace or remove all upstream dependencies/callers.")
        
        elif intent_val == "RENAME":
            actions.append("Update all direct references to the component.")
            if evidence.has_database:
                actions.append("Create a database migration script for renamed models/tables.")
                tests.append("Verify data integrity post-migration.")
                alternatives.append("Use an alias to map the old name to the new name without breaking consumers.")

        elif intent_val in ["ADD_FEATURE", "PLANNING"]:
            actions.append("Define the API contracts before implementation.")
            actions.append("Implement the feature within the recommended module boundary.")
            if evidence.has_database:
                actions.append("Design new database schema changes.")
            alternatives.append("Extend an existing component instead of creating a new one.")

        elif intent_val == "REFACTOR":
            if decision == DecisionType.REFACTOR_HIGH_RISK:
                actions.append("Create a detailed refactoring plan breaking it down into smaller PRs.")
                actions.append("Establish baseline metrics before modifying code.")
                alternatives.append("Apply the Strangler Fig pattern to gradually replace the component.")
            else:
                actions.append("Refactor the component directly.")
            tests.append("Ensure 100% test coverage of existing behavior before refactoring.")

        # 2. Evidence-based dynamic recommendations
        if evidence.has_apis:
            actions.append("Update API documentation and OpenAPI schemas.")
            tests.append("Verify API contracts with integration tests.")
            
        if evidence.has_database:
            tests.append("Run database integration tests.")
            
        if evidence.has_workflows:
            actions.append("Verify impacted workflows continue to function as expected.")
            tests.append("Execute end-to-end (E2E) workflow tests.")
            
        if not evidence.has_tests:
            tests.append(f"Write unit tests for {evidence.target_name}.")

        return actions, tests, alternatives
