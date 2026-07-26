"""
Capabilities Package (Contracts Only).
"""

from graph_query_engine.capabilities.contracts import (
    ICapabilityRegistry,
    ICapabilityValidator,
)

__all__ = ["ICapabilityRegistry", "ICapabilityValidator"]
