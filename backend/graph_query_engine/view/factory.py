"""
GraphView Factory for Validated GraphView Instantiation.
"""

from typing import Optional

from graph_query_engine.errors import ValidationError
from graph_query_engine.view.builder import GraphViewBuilder
from graph_query_engine.view.graph_view import GraphView
from graph_query_engine.view.lifecycle import (
    GraphViewLifecycle,
    GraphViewLifecycleState,
)
from graph_query_engine.view.validation import (
    GraphViewValidationReport,
    GraphViewValidator,
)


class GraphViewFactory:
    """
    Factory constructing and validating immutable GraphView instances.
    """

    @classmethod
    def create_from_builder(
        cls,
        builder: GraphViewBuilder,
        lifecycle: Optional[GraphViewLifecycle] = None,
    ) -> GraphView:
        """
        Builds and validates GraphView from a builder instance.

        Raises ValidationError if graph validation fails.
        """
        lc = lifecycle or GraphViewLifecycle()
        lc.transition_to(GraphViewLifecycleState.BUILDING)

        try:
            unvalidated_view = builder.build()
        except Exception as e:
            lc.transition_to(GraphViewLifecycleState.FAILED, error=str(e))
            raise ValidationError(
                message=f"Failed to build GraphView: {e}",
                cause=e,
            ) from e

        lc.transition_to(GraphViewLifecycleState.VALIDATING)
        report: GraphViewValidationReport = GraphViewValidator.validate(unvalidated_view)

        if not report.is_valid:
            err_msgs = "; ".join(f"[{v.category}:{v.rule_name}] {v.message}" for v in report.violations)
            lc.transition_to(GraphViewLifecycleState.FAILED, error=err_msgs)
            raise ValidationError(
                message=f"GraphView validation failed: {err_msgs}",
                metadata={"violations": [v.model_dump() for v in report.violations]},
            )

        lc.transition_to(GraphViewLifecycleState.READY)
        return unvalidated_view


__all__ = ["GraphViewFactory"]
