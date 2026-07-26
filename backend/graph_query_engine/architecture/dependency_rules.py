"""
Layering and Dependency Rules Matrix.

Defines allowed import relationships between packages in Graph Query Engine.
"""

from typing import Final

# Layer hierarchy (Lower numbers are foundational infrastructure; higher numbers depend on lower)
LAYER_HIERARCHY: Final[dict[str, int]] = {
    "types": 10,
    "constants": 10,
    "errors": 20,
    "config": 30,
    "logging": 30,
    "lifecycle": 30,
    "shared": 40,
    "utils": 40,
    "contracts": 50,
    "view": 60,
    "adapter": 60,
    "index": 60,
    "budget": 60,
    "capabilities": 60,
    "diagnostics": 60,
    "model": 60,
    "traversal": 70,
    "planner": 80,
    "pipeline": 90,
    "core": 100,
    "api": 110,
}

# Forbidden direct import targets for external packages
FORBIDDEN_EXTERNAL_IMPORTS: Final[tuple[str, ...]] = (
    "graph_query_engine.internal",
)


__all__ = ["LAYER_HIERARCHY", "FORBIDDEN_EXTERNAL_IMPORTS"]
