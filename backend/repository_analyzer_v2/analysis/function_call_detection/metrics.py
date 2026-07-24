"""
analysis/function_call_detection/metrics.py
--------------------------------------------
Phase 4.7.2 — Function Call Telemetry Metrics Helpers.

Provides utility functions for calculating and summarizing `CallMetrics`
from call records and detection outcomes.
"""

from __future__ import annotations

import os
from typing import List

from models.call_models import CallMetrics, CallRecord, CallType


def compute_metrics(
    call_records: List[CallRecord],
    build_duration_ms: float = 0.0,
    average_lookup_time_us: float = 0.0,
) -> CallMetrics:
    """
    Compute CallMetrics telemetry from a list of CallRecord objects.

    Parameters
    ----------
    call_records:
        List of processed CallRecord instances.
    build_duration_ms:
        Total duration in milliseconds.
    average_lookup_time_us:
        Average index query time in microseconds.

    Returns
    -------
    CallMetrics
    """
    total = len(call_records)
    resolved = sum(1 for c in call_records if c.callee_symbol_id is not None)
    unresolved = total - resolved

    method_calls = sum(1 for c in call_records if c.is_method or c.call_type in (CallType.METHOD, CallType.CLASS_METHOD, CallType.STATIC_METHOD))
    constructor_calls = sum(1 for c in call_records if c.is_constructor or c.call_type == CallType.CONSTRUCTOR)
    async_calls = sum(1 for c in call_records if c.is_async or c.call_type == CallType.ASYNC)
    lambda_calls = sum(1 for c in call_records if c.is_lambda or c.call_type == CallType.LAMBDA)
    external_calls = sum(1 for c in call_records if c.is_external)

    return CallMetrics(
        total_calls=total,
        resolved_calls=resolved,
        unresolved_calls=unresolved,
        method_calls=method_calls,
        constructor_calls=constructor_calls,
        async_calls=async_calls,
        lambda_calls=lambda_calls,
        external_calls=external_calls,
        average_lookup_time_us=round(average_lookup_time_us, 3),
        build_duration_ms=round(build_duration_ms, 3),
        memory_bytes=_get_memory_bytes(),
    )


def _get_memory_bytes() -> int:
    """Return process RSS memory footprint in bytes, or 0 if psutil unavailable."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss
    except Exception:
        return 0
