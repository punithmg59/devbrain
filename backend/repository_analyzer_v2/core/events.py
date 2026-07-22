from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import inspect
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core Event Hierarchy
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """Base class for all system events."""
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class PipelineStarted(Event):
    run_id: str = ""
    repository_id: str = ""
    stages: List[str] = field(default_factory=list)


@dataclass
class PipelineFinished(Event):
    run_id: str = ""
    repository_id: str = ""
    total_duration_ms: float = 0.0
    stages_completed: List[str] = field(default_factory=list)


@dataclass
class StageStarted(Event):
    run_id: str = ""
    stage_name: str = ""


@dataclass
class StageFinished(Event):
    run_id: str = ""
    stage_name: str = ""
    duration_ms: float = 0.0


@dataclass
class StageFailed(Event):
    run_id: str = ""
    stage_name: str = ""
    error: Optional[Exception] = None
    duration_ms: float = 0.0


@dataclass
class PluginLoaded(Event):
    plugin_name: str = ""
    language: str = ""
    version: str = ""


@dataclass
class PluginFailed(Event):
    plugin_name: str = ""
    error: Optional[Exception] = None


@dataclass
class AnalysisStarted(Event):
    analysis_id: str = ""
    repository_id: str = ""


@dataclass
class AnalysisFinished(Event):
    analysis_id: str = ""
    repository_id: str = ""
    duration_ms: float = 0.0
    status: str = "completed"


# Handler type definition (sync or async callable)
EventHandler = Callable[[Any], Any]


# ---------------------------------------------------------------------------
# Thread-safe EventBus
# ---------------------------------------------------------------------------

class EventBus:
    """
    Thread-safe, sync and async supporting internal event bus.
    """
    _instance: Optional[EventBus] = None
    _singleton_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._subscribers: Dict[Type[Event], Set[EventHandler]] = {}
        self._wildcard_subscribers: Set[EventHandler] = set()
        self._lock: threading.Lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> EventBus:
        """Singleton accessor for global EventBus."""
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def subscribe(self, event_type: Optional[Type[Event]], handler: EventHandler) -> None:
        """
        Subscribe a handler function (sync or async) to a specific event type.
        If event_type is Event or None, subscribes to ALL events (wildcard).
        """
        with self._lock:
            if event_type is None or event_type is Event:
                self._wildcard_subscribers.add(handler)
            else:
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = set()
                self._subscribers[event_type].add(handler)

    def unsubscribe(self, event_type: Optional[Type[Event]], handler: EventHandler) -> bool:
        """
        Unsubscribe a handler from a specific event type or wildcard.
        Returns True if handler was found and removed, False otherwise.
        """
        with self._lock:
            if event_type is None or event_type is Event:
                if handler in self._wildcard_subscribers:
                    self._wildcard_subscribers.remove(handler)
                    return True
                return False
            else:
                if event_type in self._subscribers and handler in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(handler)
                    if not self._subscribers[event_type]:
                        del self._subscribers[event_type]
                    return True
                return False

    def clear(self) -> None:
        """Reset all subscriptions."""
        with self._lock:
            self._subscribers.clear()
            self._wildcard_subscribers.clear()

    def _get_handlers_for(self, event: Event) -> List[EventHandler]:
        """Fetch snapshot of handlers for an event."""
        with self._lock:
            event_type = type(event)
            specific = list(self._subscribers.get(event_type, set()))
            wildcard = list(self._wildcard_subscribers)
            return specific + wildcard

    def publish(self, event: Event) -> None:
        """
        Synchronously publish an event to all subscribers.
        Calls sync handlers immediately and schedules async handlers on active event loop if available.
        """
        handlers = self._get_handlers_for(event)
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(event))
                    except RuntimeError:
                        # No running loop, execute coroutine in a new loop
                        asyncio.run(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler '{handler}' for event '{type(event).__name__}': {e}", exc_info=True)

    async def publish_async(self, event: Event) -> None:
        """
        Asynchronously publish an event, awaiting async handlers and running sync handlers.
        """
        handlers = self._get_handlers_for(event)
        async_tasks = []
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    async_tasks.append(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in sync event handler '{handler}' during publish_async: {e}", exc_info=True)

        if async_tasks:
            results = await asyncio.gather(*async_tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Error in async event handler during publish_async: {res}", exc_info=True)
