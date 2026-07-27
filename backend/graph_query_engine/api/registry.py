"""
Public Query API Registry.

Thread-safe registry for custom query operations, query handlers, and active sessions.
"""

import threading
from typing import Any, Callable, Dict, Optional, Tuple
from graph_query_engine.api.exceptions import PublicQueryApiException


class QueryRegistry:
    """
    Thread-safe registry for Public Query API handlers and sessions.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._sessions: Dict[str, Any] = {}

    def register_handler(self, operation: str, handler: Callable[..., Any]) -> None:
        """Registers a custom query handler for an operation name."""
        with self._lock:
            if not operation:
                raise PublicQueryApiException("Operation name cannot be empty for handler registration")
            self._handlers[operation] = handler

    def get_handler(self, operation: str) -> Optional[Callable[..., Any]]:
        """Retrieves a registered custom query handler by operation name."""
        with self._lock:
            return self._handlers.get(operation)

    def register_session(self, session_id: str, session: Any) -> None:
        """Registers an active session."""
        with self._lock:
            self._sessions[session_id] = session

    def get_session(self, session_id: str) -> Optional[Any]:
        """Retrieves a registered session."""
        with self._lock:
            return self._sessions.get(session_id)

    def unregister_session(self, session_id: str) -> bool:
        """Unregisters a session."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def list_handlers(self) -> Tuple[str, ...]:
        """Returns tuple of registered handler operation names."""
        with self._lock:
            return tuple(self._handlers.keys())


__all__ = ["QueryRegistry"]
