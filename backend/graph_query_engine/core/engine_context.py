"""
Engine Execution Context Container Placeholder.

Infrastructure placeholder only - NO business logic in Step 1.1.
"""

from dataclasses import dataclass
from typing import Optional

from graph_query_engine.config import GraphQueryEngineConfig
from graph_query_engine.types import CorrelationId, RequestId


@dataclass(frozen=True)
class EngineExecutionContext:
    """
    Container holding engine-wide execution context and configuration.
    """
    config: GraphQueryEngineConfig
    correlation_id: CorrelationId
    request_id: Optional[RequestId] = None


__all__ = ["EngineExecutionContext"]
