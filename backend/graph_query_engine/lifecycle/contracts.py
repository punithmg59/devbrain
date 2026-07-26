"""
Lifecycle Component Protocol for Graph Query Engine.
"""

from typing import Protocol

from graph_query_engine.lifecycle.enums import LifecycleState
from graph_query_engine.lifecycle.models import LifecycleStatus


class LifecycleComponent(Protocol):
    """
    Contract for components participating in the engine lifecycle.
    """

    def initialize(self) -> None:
        """
        Initializes the component resource allocations.
        """
        ...

    def shutdown(self) -> None:
        """
        Gracefully releases component resources and prepares for shutdown.
        """
        ...

    def get_state(self) -> LifecycleState:
        """
        Returns current lifecycle state of the component.
        """
        ...

    def get_status(self) -> LifecycleStatus:
        """
        Returns a complete status object for the component.
        """
        ...
