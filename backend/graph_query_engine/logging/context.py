"""
Correlation Context Holder for Graph Query Engine Logging.
"""

from dataclasses import dataclass
from typing import Optional

from graph_query_engine.types import CorrelationId, RequestId


@dataclass(frozen=True)
class CorrelationContext:
    """
    Holds tracking identifiers for end-to-end query trace correlation.
    """
    correlation_id: CorrelationId
    request_id: Optional[RequestId] = None

    @classmethod
    def create(
        self,
        correlation_id: str,
        request_id: Optional[str] = None,
    ) -> "CorrelationContext":
        """
        Factory helper to create a CorrelationContext instance.
        """
        return CorrelationContext(
            correlation_id=CorrelationId(correlation_id),
            request_id=RequestId(request_id) if request_id else None,
        )
