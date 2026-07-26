"""
Capabilities Contracts Re-export.
"""

from graph_query_engine.contracts.capabilities import (
    ICapabilityRegistry,
    ICapabilityValidator,
)

__all__ = ["ICapabilityRegistry", "ICapabilityValidator"]
