"""
analysis/re_export_resolution/metrics.py
-----------------------------------------
Phase 4.7.1 — Re-Export Resolution Metrics Helpers.

Provides utility functions for collecting and computing ReExportMetrics
from export records and resolution outcomes.
"""

from __future__ import annotations

import os
from typing import List, Optional

from models.re_export_models import ExportRecord, ExportType, ReExportMetrics


def compute_metrics(
    export_records: List[ExportRecord],
    build_duration_ms: float = 0.0,
) -> ReExportMetrics:
    """
    Compute ReExportMetrics from a list of resolved ExportRecord objects.

    Parameters
    ----------
    export_records:
        All ExportRecord objects produced by ReExportBuilder and resolved by
        ReExportResolver.
    build_duration_ms:
        Total build and resolution duration in milliseconds.

    Returns
    -------
    ReExportMetrics
    """
    total = len(export_records)
    resolved = sum(1 for r in export_records if r.is_resolved)
    failed = total - resolved
    star_exports = sum(1 for r in export_records if r.is_star_export)
    all_list = sum(1 for r in export_records if r.export_type in (ExportType.ALL_LIST, ExportType.ALL_AUGMENTED, ExportType.ALL_APPEND))
    alias_exports = sum(1 for r in export_records if r.export_type == ExportType.FROM_IMPORT_ALIAS)

    packages_scanned = len({r.package_fqn for r in export_records})

    return ReExportMetrics(
        total_packages_scanned=packages_scanned,
        total_exports_found=total,
        total_exports_resolved=resolved,
        total_exports_failed=failed,
        star_exports=star_exports,
        all_list_exports=all_list,
        alias_exports=alias_exports,
        build_duration_ms=round(build_duration_ms, 3),
        memory_bytes=_get_memory_bytes(),
    )


def _get_memory_bytes() -> int:
    """Return current process RSS memory in bytes, or 0 if psutil unavailable."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss
    except Exception:
        return 0
