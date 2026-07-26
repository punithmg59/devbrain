"""
Lifecycle Enumerations for Graph Query Engine.
"""

from enum import StrEnum


class EngineState(StrEnum):
    """
    Standard operational states of the Graph Query Engine lifecycle.
    """
    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    FAILED = "FAILED"
    SHUTDOWN = "SHUTDOWN"


class LifecycleState(StrEnum):
    """
    Transition states for engine components during lifecycle events.
    """
    UNINITIALIZED = "UNINITIALIZED"
    STARTING = "STARTING"
    ACTIVE = "ACTIVE"
    STOPPING = "STOPPING"
    TERMINATED = "TERMINATED"
    ERROR = "ERROR"
