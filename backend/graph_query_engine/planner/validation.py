"""
PlannerValidation for Infrastructure Object Auditing.
"""

from typing import Optional
from graph_query_engine.errors import InvalidPlannerConfigError, ValidationError
from graph_query_engine.planner.config import PlannerConfiguration, PlanningBudget
from graph_query_engine.planner.context import PlannerContext
from graph_query_engine.planner.session import PlannerSession


class PlannerValidation:
    """
    Infrastructure validator for PlannerContext, PlannerConfiguration, PlanningBudget, and PlannerSession.
    Does NOT validate Query AST or execution plans.
    """

    @classmethod
    def validate_budget(cls, budget: PlanningBudget) -> None:
        """Validates PlanningBudget fields."""
        if budget is None:
            raise InvalidPlannerConfigError("PlanningBudget cannot be None.")
        budget.validate_budget()

    @classmethod
    def validate_configuration(cls, config: PlannerConfiguration) -> None:
        """Validates PlannerConfiguration fields."""
        if config is None:
            raise InvalidPlannerConfigError("PlannerConfiguration cannot be None.")
        cls.validate_budget(config.budget)

    @classmethod
    def validate_context(cls, context: PlannerContext) -> None:
        """Validates PlannerContext fields."""
        if context is None:
            raise ValidationError("PlannerContext cannot be None.")
        if not context.session_id:
            raise ValidationError("PlannerContext session_id cannot be empty.")
        cls.validate_configuration(context.configuration)
        cls.validate_budget(context.budget)

    @classmethod
    def validate_session(cls, session: PlannerSession) -> None:
        """Validates PlannerSession fields."""
        if session is None:
            raise ValidationError("PlannerSession cannot be None.")
        if not session.session_id:
            raise ValidationError("PlannerSession session_id cannot be empty.")


__all__ = ["PlannerValidation"]
