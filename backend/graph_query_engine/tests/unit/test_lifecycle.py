"""
Unit tests for Lifecycle Definitions.
"""

from datetime import datetime
from graph_query_engine.lifecycle import (
    EngineState,
    EngineStatus,
    LifecycleEvent,
    LifecycleState,
    LifecycleStatus,
)


def test_engine_state_enum():
    states = [e.value for e in EngineState]
    assert "CREATED" in states
    assert "INITIALIZING" in states
    assert "READY" in states
    assert "FAILED" in states
    assert "SHUTDOWN" in states


def test_lifecycle_models():
    event = LifecycleEvent(
        component_name="QueryEngine",
        previous_state=EngineState.CREATED,
        new_state=EngineState.INITIALIZING,
    )
    assert event.component_name == "QueryEngine"
    assert event.previous_state == EngineState.CREATED
    assert event.new_state == EngineState.INITIALIZING

    status = LifecycleStatus(
        component_name="CacheIndex",
        state=LifecycleState.ACTIVE,
    )
    assert status.component_name == "CacheIndex"
    assert status.state == LifecycleState.ACTIVE

    engine_status = EngineStatus(
        engine_name="DevBrainGQE",
        version="1.0.0",
        state=EngineState.READY,
        uptime_seconds=120.5,
        components=(status,),
    )
    assert engine_status.engine_name == "DevBrainGQE"
    assert engine_status.state == EngineState.READY
    assert len(engine_status.components) == 1
