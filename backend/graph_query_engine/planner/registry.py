"""
PlannerRegistry Extension Infrastructure for Query Planner.
"""

import threading
from typing import Any, Mapping, Optional

from graph_query_engine.errors import PlannerRegistryError


class PlannerRegistry:
    """
    Thread-safe registry managing planner extensions (optimizers, validators, physical planners, diagnostics listeners).
    Infrastructure only.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._extensions: dict[str, dict[str, Any]] = {}

    def register_extension(self, category: str, name: str, extension: Any) -> None:
        """
        Registers an extension object under category and name.
        Raises PlannerRegistryError if inputs are empty or extension is None.
        """
        if not category or not name:
            raise PlannerRegistryError("Category and name strings cannot be empty.")
        if extension is None:
            raise PlannerRegistryError("Extension instance cannot be None.")

        cat_clean = category.lower()
        name_clean = name.lower()

        with self._lock:
            if cat_clean not in self._extensions:
                self._extensions[cat_clean] = {}
            self._extensions[cat_clean][name_clean] = extension

    def get_extension(self, category: str, name: str) -> Optional[Any]:
        """Retrieves registered extension or returns None if missing."""
        cat_clean = category.lower()
        name_clean = name.lower()
        with self._lock:
            return self._extensions.get(cat_clean, {}).get(name_clean)

    def contains(self, category: str, name: str) -> bool:
        """Returns True if category and name extension is registered."""
        return self.get_extension(category, name) is not None

    def list_extensions(self, category: Optional[str] = None) -> tuple[str, ...]:
        """Returns tuple of registered extension names for category or all categories."""
        with self._lock:
            if category:
                return tuple(self._extensions.get(category.lower(), {}).keys())
            names = []
            for cat_map in self._extensions.values():
                names.extend(cat_map.keys())
            return tuple(names)


__all__ = ["PlannerRegistry"]
