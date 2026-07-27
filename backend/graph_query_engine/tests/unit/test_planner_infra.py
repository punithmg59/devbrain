"""
Comprehensive unit test suite for Step 4.1 Planner Core Infrastructure.
"""

from concurrent.futures import ThreadPoolExecutor
import pytest

from graph_query_engine.contracts.planner import (
    IPlannerCapabilities,
    IPlannerContext,
    IPlannerDiagnostics,
    IPlannerLifecycle,
    IPlannerRegistry,
    IPlannerSession,
)
from graph_query_engine.errors import (
    BudgetExceededError,
    CapabilityUnsupportedError,
    InvalidPlannerConfigError,
    InvalidPlannerStateError,
    PlannerRegistryError,
    ValidationError,
)
from graph_query_engine.planner import (
    CapabilityFlag,
    DiagnosticEvent,
    EventLevel,
    MetricsCollector,
    PlannerCapabilities,
    PlannerConfiguration,
    PlannerContext,
    PlannerDiagnostics,
    PlannerLifecycle,
    PlannerMetrics,
    PlannerRegistry,
    PlannerSession,
    PlannerState,
    PlannerValidation,
    PlannerVersion,
    PlanningBudget,
)


def test_planner_version():
    ver = PlannerVersion(major=4, minor=1, patch=0, planner_generation=1)
    assert str(ver) == "4.1.0-gen1"
    assert ver.is_compatible_with("4.0.0") is True
    assert ver.is_compatible_with("5.0.0") is False


def test_planner_state_transitions():
    lc = PlannerLifecycle(initial_state=PlannerState.CREATED)
    assert lc.current_state == PlannerState.CREATED
    assert lc.is_terminal() is False

    lc.transition_to(PlannerState.INITIALIZED)
    assert lc.current_state == PlannerState.INITIALIZED

    lc.transition_to(PlannerState.VALIDATING)
    lc.transition_to(PlannerState.PLANNING)
    lc.transition_to(PlannerState.OPTIMIZING)
    lc.transition_to(PlannerState.BUILDING_PLAN)
    lc.transition_to(PlannerState.COMPLETED)
    assert lc.is_terminal() is True

    with pytest.raises(InvalidPlannerStateError):
        lc.transition_to(PlannerState.PLANNING)


def test_invalid_planner_state_transition():
    lc = PlannerLifecycle(initial_state=PlannerState.CREATED)
    with pytest.raises(InvalidPlannerStateError):
        lc.transition_to(PlannerState.BUILDING_PLAN)


def test_planner_configuration_and_budget():
    budget = PlanningBudget(timeout_seconds=15.0, max_planning_stages=5)
    config = PlannerConfiguration(optimization_enabled=True, debug_mode=False, budget=budget)
    assert config.budget.timeout_seconds == 15.0

    bad_budget = PlanningBudget.model_construct(timeout_seconds=-1.0)
    with pytest.raises(InvalidPlannerConfigError):
        PlannerValidation.validate_budget(bad_budget)


def test_planner_capabilities():
    caps = PlannerCapabilities()
    assert caps.is_supported(CapabilityFlag.LOGICAL_PLANNING) is True
    assert caps.is_supported(CapabilityFlag.DISTRIBUTED_PLANNING) is False

    caps.require_capability(CapabilityFlag.LOGICAL_PLANNING)
    with pytest.raises(CapabilityUnsupportedError):
        caps.require_capability(CapabilityFlag.DISTRIBUTED_PLANNING)


def test_planner_diagnostics():
    diag = PlannerDiagnostics()
    diag.record_event(EventLevel.INFO, "Planner context initialized", stage_name="Init")
    diag.record_event(EventLevel.STAGE_START, "Validation stage started", stage_name="Validation")

    assert diag.count() == 2
    assert diag.has_errors() is False
    events = diag.get_events()
    assert events[0].stage_name == "Init"


def test_planner_metrics():
    collector = MetricsCollector()
    collector.record_stage_duration("Validation", 12.5)
    collector.increment_optimizations()
    collector.set_total_planning_time(0.045)

    metrics = collector.get_metrics()
    assert metrics.planning_time_seconds == 0.045
    assert metrics.stage_durations_ms["Validation"] == 12.5
    assert metrics.optimization_count == 1


def test_planner_context_immutability():
    ctx = PlannerContext(
        session_id="psess_123",
        correlation_id="corr_456",
        query_metadata={"raw_query": "MATCH (n) RETURN n"},
        snapshot_metadata_ref={"snap_id": "snap_001"},
    )
    assert ctx.session_id == "psess_123"
    assert ctx.current_state == "CREATED"

    with pytest.raises(Exception):
        ctx.session_id = "psess_999"


def test_planner_session():
    session = PlannerSession(correlation_id="corr_abc")
    assert session.session_id.startswith("psess_")
    lc = session.create_lifecycle()
    assert lc.current_state == PlannerState.CREATED


def test_planner_validation():
    session = PlannerSession()
    ctx = PlannerContext(session_id=session.session_id)

    PlannerValidation.validate_session(session)
    PlannerValidation.validate_context(ctx)

    bad_ctx = PlannerContext(session_id="")
    with pytest.raises(ValidationError):
        PlannerValidation.validate_context(bad_ctx)


def test_planner_registry():
    reg = PlannerRegistry()
    reg.register_extension("optimizer", "rule_pass_1", "DummyOptimizerObject")

    assert reg.contains("optimizer", "rule_pass_1") is True
    ext = reg.get_extension("optimizer", "rule_pass_1")
    assert ext == "DummyOptimizerObject"

    with pytest.raises(PlannerRegistryError):
        reg.register_extension("", "name", "obj")


def test_planner_contracts_runtime_checkable():
    ctx = PlannerContext(session_id="sess_1")
    assert isinstance(ctx, IPlannerContext)

    session = PlannerSession()
    assert isinstance(session, IPlannerSession)

    caps = PlannerCapabilities()
    assert isinstance(caps, IPlannerCapabilities)

    diag = PlannerDiagnostics()
    assert isinstance(diag, IPlannerDiagnostics)

    lc = PlannerLifecycle()
    assert isinstance(lc, IPlannerLifecycle)

    reg = PlannerRegistry()
    assert isinstance(reg, IPlannerRegistry)


def test_thread_safe_parallel_planner_operations():
    session = PlannerSession()
    diag = PlannerDiagnostics()
    collector = MetricsCollector()

    def worker(i):
        diag.record_event(EventLevel.INFO, f"Event {i}", stage_name=f"Stage_{i}")
        collector.record_stage_duration(f"Stage_{i}", float(i))
        collector.increment_optimizations()

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(100)]
        for f in futures:
            f.result()

    assert diag.count() == 100
    metrics = collector.get_metrics()
    assert metrics.optimization_count == 100
