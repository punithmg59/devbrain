"""
Lifecycle Data Models for Graph Query Engine.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from graph_query_engine.lifecycle.enums import EngineState, LifecycleState


@dataclass(frozen=True)
class LifecycleEvent:
    """
    Immutable representation of a state change event in engine lifecycle.
    """
    component_name: str
    previous_state: LifecycleState | EngineState
    new_state: LifecycleState | EngineState
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class LifecycleStatus:
    """
    Status snapshot for an individual lifecycle component.
    """
    component_name: str
    state: LifecycleState
    initialized_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class EngineStatus:
    """
    Overall status summary for the entire Graph Query Engine.
    """
    engine_name: str
    version: str
    state: EngineState
    uptime_seconds: float
    components: tuple[LifecycleStatus, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
