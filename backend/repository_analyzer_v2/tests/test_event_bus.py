import asyncio
import threading
import time
import pytest

from core.events import (
    AnalysisFinished,
    AnalysisStarted,
    Event,
    EventBus,
    PipelineFinished,
    PipelineStarted,
    PluginFailed,
    PluginLoaded,
    StageFailed,
    StageFinished,
    StageStarted,
)


@pytest.fixture(autouse=True)
def reset_event_bus():
    bus = EventBus.get_instance()
    bus.clear()
    yield bus
    bus.clear()


def test_all_events_instantiation():
    """Test instantiating all required event types."""
    p_start = PipelineStarted(run_id="run-1", repository_id="repo-1", stages=["Discovery"])
    p_finish = PipelineFinished(run_id="run-1", repository_id="repo-1", total_duration_ms=120.0)
    s_start = StageStarted(run_id="run-1", stage_name="Discovery")
    s_finish = StageFinished(run_id="run-1", stage_name="Discovery", duration_ms=10.0)
    s_fail = StageFailed(run_id="run-1", stage_name="Discovery", error=ValueError("bad stage"))
    plug_load = PluginLoaded(plugin_name="PyPlugin", language="python", version="1.0.0")
    plug_fail = PluginFailed(plugin_name="PyPlugin", error=RuntimeError("init failed"))
    a_start = AnalysisStarted(analysis_id="analysis-1", repository_id="repo-1")
    a_finish = AnalysisFinished(analysis_id="analysis-1", repository_id="repo-1", duration_ms=500.0, status="completed")

    assert p_start.run_id == "run-1"
    assert p_finish.total_duration_ms == 120.0
    assert s_start.stage_name == "Discovery"
    assert s_finish.duration_ms == 10.0
    assert isinstance(s_fail.error, ValueError)
    assert plug_load.language == "python"
    assert isinstance(plug_fail.error, RuntimeError)
    assert a_start.analysis_id == "analysis-1"
    assert a_finish.status == "completed"


def test_subscribe_and_publish_sync(reset_event_bus):
    """Test sync event handler subscription and publishing."""
    received = []

    def handler(event: StageStarted):
        received.append(event)

    reset_event_bus.subscribe(StageStarted, handler)
    
    event = StageStarted(run_id="run-1", stage_name="Parser")
    reset_event_bus.publish(event)

    assert len(received) == 1
    assert received[0] is event


def test_wildcard_subscription(reset_event_bus):
    """Test subscribing to all events using wildcard/Event type."""
    received = []

    def wildcard_handler(event: Event):
        received.append(event)

    reset_event_bus.subscribe(Event, wildcard_handler)

    e1 = PipelineStarted(run_id="r1")
    e2 = PluginLoaded(plugin_name="P1")

    reset_event_bus.publish(e1)
    reset_event_bus.publish(e2)

    assert len(received) == 2
    assert received == [e1, e2]


def test_unsubscribe(reset_event_bus):
    """Test unsubscribing handlers."""
    received = []

    def handler(event: AnalysisStarted):
        received.append(event)

    reset_event_bus.subscribe(AnalysisStarted, handler)
    reset_event_bus.publish(AnalysisStarted(analysis_id="a1"))
    assert len(received) == 1

    removed = reset_event_bus.unsubscribe(AnalysisStarted, handler)
    assert removed is True

    reset_event_bus.publish(AnalysisStarted(analysis_id="a2"))
    assert len(received) == 1


@pytest.mark.asyncio
async def test_async_publish_and_handlers(reset_event_bus):
    """Test publishing asynchronously to async handlers."""
    received = []

    async def async_handler(event: PipelineFinished):
        await asyncio.sleep(0.01)
        received.append(event)

    reset_event_bus.subscribe(PipelineFinished, async_handler)

    event = PipelineFinished(run_id="r1", total_duration_ms=100.0)
    await reset_event_bus.publish_async(event)

    assert len(received) == 1
    assert received[0] is event


def test_handler_error_isolation(reset_event_bus):
    """Test that a failing handler does not prevent other handlers from running."""
    received = []

    def bad_handler(event: StageFailed):
        raise RuntimeError("Handler crash!")

    def good_handler(event: StageFailed):
        received.append(event)

    reset_event_bus.subscribe(StageFailed, bad_handler)
    reset_event_bus.subscribe(StageFailed, good_handler)

    event = StageFailed(run_id="r1", stage_name="Linker")
    reset_event_bus.publish(event)

    assert len(received) == 1
    assert received[0] is event


def test_thread_safety():
    """Test concurrent subscriptions and publishing across multiple threads."""
    bus = EventBus()
    bus.clear()

    count = 0
    lock = threading.Lock()

    def worker(i: int):
        def handler(event: PluginLoaded):
            nonlocal count
            with lock:
                count += 1

        bus.subscribe(PluginLoaded, handler)
        bus.publish(PluginLoaded(plugin_name=f"p-{i}"))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert count >= 20
