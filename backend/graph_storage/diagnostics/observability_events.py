"""
Observability event model interfaces.
"""

from dataclasses import dataclass, field
import time


@dataclass(frozen=True)
class OperationStartedEvent:
    operation: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class OperationCompletedEvent:
    operation: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class OperationFailedEvent:
    operation: str
    error_message: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class MetricRecordedEvent:
    metric_name: str
    value: float
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class HealthCheckedEvent:
    status: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class DiagnosticGeneratedEvent:
    report_severity: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class AlertRaisedEvent:
    alert_id: str
    severity: str
    message: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class TraceStartedEvent:
    trace_id: str
    operation: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class TraceCompletedEvent:
    trace_id: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)
