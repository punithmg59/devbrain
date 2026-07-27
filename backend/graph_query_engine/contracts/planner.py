"""
Planner Infrastructure Contract Protocols for Graph Query Engine.
"""

from datetime import datetime
from typing import Any, Mapping, Optional, Protocol, runtime_checkable


@runtime_checkable
class IPlannerCapabilities(Protocol):
    """Protocol for planner capability querying and registry."""

    def is_supported(self, feature: str) -> bool:
        """Returns True if feature is supported."""
        ...

    def list_capabilities(self) -> tuple[str, ...]:
        """Returns tuple of all advertised capabilities."""
        ...


@runtime_checkable
class IPlannerDiagnostics(Protocol):
    """Protocol for collecting planner events, warnings, timing, and trace messages."""

    def record_event(self, event_type: str, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """Records a planner diagnostic event."""
        ...

    def get_events(self) -> tuple[Any, ...]:
        """Retrieves recorded diagnostic events."""
        ...


@runtime_checkable
class IPlannerContext(Protocol):
    """Protocol for immutable planner stage context."""

    @property
    def session_id(self) -> str:
        """Unique session identifier string."""
        ...

    @property
    def correlation_id(self) -> str:
        """Correlation ID for distributed request tracing."""
        ...

    @property
    def current_state(self) -> str:
        """Planner lifecycle state string."""
        ...


@runtime_checkable
class IPlannerSession(Protocol):
    """Protocol for planning request session lifecycle."""

    @property
    def session_id(self) -> str:
        """Unique session ID."""
        ...

    @property
    def created_at(self) -> datetime:
        """Session UTC creation timestamp."""
        ...


@runtime_checkable
class IPlannerLifecycle(Protocol):
    """Protocol for managing planner state transitions."""

    def transition_to(self, new_state: str) -> None:
        """Transitions lifecycle to new_state."""
        ...

    def is_terminal(self) -> bool:
        """Returns True if lifecycle has reached a terminal state."""
        ...


@runtime_checkable
class IPlannerRegistry(Protocol):
    """Protocol for planner extension registration and lookup."""

    def register_extension(self, category: str, name: str, extension: Any) -> None:
        """Registers a planner extension under category and name."""
        ...

    def get_extension(self, category: str, name: str) -> Optional[Any]:
        """Retrieves registered extension or None."""
        ...


@runtime_checkable
class IQueryPlanner(Protocol):
    """Protocol for high-level query planning and optimization."""

    def create_plan(self, query_ast: Any, context: Any) -> Any:
        """Generates an optimized execution plan from input AST and context."""
        ...


__all__ = [
    "IPlannerCapabilities",
    "IPlannerDiagnostics",
    "IPlannerContext",
    "IPlannerSession",
    "IPlannerLifecycle",
    "IPlannerRegistry",
    "IQueryPlanner",
]
