"""
Follow-up Engine (Layer 3)

Generates intelligent follow-up questions deterministically.
"""

from typing import List

from app.services.intent.schemas import Intent
from app.services.reasoning.schemas.engineering_decision import DecisionType


class FollowupEngine:
    """Generates intent-aware follow-up questions."""

    def generate_questions(self, intent: Intent, decision: DecisionType) -> List[str]:
        """
        Generate follow-up questions based on the intent and decision.
        """
        questions = []
        intent_val = intent.intent.value if hasattr(intent.intent, 'value') else str(intent.intent).upper()
        
        if intent_val == "DELETE":
            if decision == DecisionType.DO_NOT_DELETE:
                questions.append("What breaks if I rename instead?")
                questions.append("Show callers.")
                questions.append("Generate a deprecation strategy.")
            else:
                questions.append("Generate migration plan.")
                questions.append("Estimate implementation effort.")
                
        elif intent_val == "RENAME":
            questions.append("Show all affected configurations.")
            questions.append("What database tables need to be migrated?")
            questions.append("Generate migration plan.")
            
        elif intent_val in ["ADD_FEATURE", "PLANNING"]:
            questions.append("Generate implementation plan.")
            questions.append("What are the security implications of this feature?")
            questions.append("Estimate implementation effort.")
            
        elif intent_val == "REFACTOR":
            if decision == DecisionType.REFACTOR_HIGH_RISK:
                questions.append("Show critical paths affected.")
                questions.append("Generate a phased refactoring plan.")
            else:
                questions.append("Show complexity hotspots.")
                questions.append("Generate implementation plan.")
                
        elif intent_val in ["ARCHITECTURE", "EXPLAIN"]:
            questions.append("Show downstream dependencies.")
            questions.append("What is the business impact of this component?")
            questions.append("Show related workflows.")
            
        else:
            questions.append("Show callers.")
            questions.append("Show downstream dependencies.")

        return questions
