"""
analysis/optimization/resource_monitor.py
------------------------------------------
Phase 4.8.4 — Process Resource Monitor.

Monitors process RSS memory footprint, peak memory, CPU utilization, and object counters
(files, nodes, edges) during pipeline execution.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from models.optimization_models import ProcessingStage, ResourceSnapshot
from utils.logger import get_logger

logger = get_logger(__name__)


class ResourceMonitor:
    """
    Monitors process memory, CPU, and processing counters.

    Usage::

        monitor = ResourceMonitor()
        snapshot = monitor.take_snapshot(ProcessingStage.PARSING)
    """

    def __init__(self) -> None:
        self._start_time = time.time()
        self._peak_memory_mb = 0.0
        self._files_processed = 0
        self._nodes_processed = 0
        self._edges_processed = 0

    def take_snapshot(
        self,
        active_stage: ProcessingStage = ProcessingStage.DISCOVERY,
    ) -> ResourceSnapshot:
        """
        Take a point-in-time snapshot of process resource consumption and object counters.

        Parameters
        ----------
        active_stage:
            Current pipeline stage.

        Returns
        -------
        ResourceSnapshot
        """
        current_rss = self.get_current_rss_mb()
        if current_rss > self._peak_memory_mb:
            self._peak_memory_mb = current_rss

        cpu = self.get_cpu_percent()

        return ResourceSnapshot(
            timestamp=time.time(),
            memory_rss_mb=round(current_rss, 2),
            peak_memory_mb=round(self._peak_memory_mb, 2),
            cpu_percent=round(cpu, 1),
            active_stage=active_stage,
            files_processed=self._files_processed,
            nodes_processed=self._nodes_processed,
            edges_processed=self._edges_processed,
        )

    def get_current_rss_mb(self) -> float:
        """Return current process RSS memory in megabytes."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024.0 * 1024.0)
        except Exception:
            return 0.0

    def get_cpu_percent(self) -> float:
        """Return process CPU utilization percentage."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.cpu_percent(interval=None)
        except Exception:
            return 0.0

    def update_counters(
        self,
        files: Optional[int] = None,
        nodes: Optional[int] = None,
        edges: Optional[int] = None,
    ) -> None:
        """Update cumulative object counters."""
        if files is not None:
            self._files_processed = files
        if nodes is not None:
            self._nodes_processed = nodes
        if edges is not None:
            self._edges_processed = edges

    def check_memory_threshold(self, threshold_mb: float) -> bool:
        """
        Return True if current process RSS memory exceeds the configured threshold.
        """
        current_rss = self.get_current_rss_mb()
        if current_rss > self._peak_memory_mb:
            self._peak_memory_mb = current_rss
        return current_rss >= threshold_mb
