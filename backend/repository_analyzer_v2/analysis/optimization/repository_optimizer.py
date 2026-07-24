"""
analysis/optimization/repository_optimizer.py
---------------------------------------------
Phase 4.8.4 — Streaming & Memory Optimizer.

Implements streaming file batch iterators, intermediate memory cleanup triggers,
and object reference optimization for processing large repositories.

Design Principles
-----------------
- **Generator Iterators**: Stream files in configurable batches without loading all intermediate objects into RAM.
- **Explicit Memory Release**: Triggers garbage collection when memory thresholds are exceeded.
- **Zero Result Mutation**: Optimizes resource consumption without altering analysis results or graph data contracts.
"""

from __future__ import annotations

import gc
import sys
from typing import Generator, List, TypeVar

from analysis.optimization.optimization_config import OptimizationConfig
from analysis.optimization.resource_monitor import ResourceMonitor
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RepositoryOptimizer:
    """
    Optimization engine providing streaming iterators and memory management.

    Usage::

        optimizer = RepositoryOptimizer(config=OptimizationConfig(batch_size=500))
        for batch in optimizer.batch_file_iterator(all_files):
            process_batch(batch)
            optimizer.check_and_cleanup_memory(monitor)
    """

    def __init__(self, config: Optional[OptimizationConfig] = None) -> None:
        self.config = config or OptimizationConfig()

    def batch_file_iterator(
        self,
        files: List[T],
        batch_size: Optional[int] = None,
    ) -> Generator[List[T], None, None]:
        """
        Yield slice batches of files to enable streaming batch processing.

        Parameters
        ----------
        files:
            List of target items to slice.
        batch_size:
            Batch size override. Defaults to config.batch_size.

        Yields
        ------
        List[T]
        """
        sz = batch_size or self.config.batch_size
        sz = max(1, sz)
        total = len(files)

        for idx in range(0, total, sz):
            yield files[idx : idx + sz]

    def check_and_cleanup_memory(
        self,
        resource_monitor: Optional[ResourceMonitor] = None,
        force: bool = False,
    ) -> bool:
        """
        Check memory threshold and trigger garbage collection if memory limits are exceeded.

        Parameters
        ----------
        resource_monitor:
            ResourceMonitor instance.
        force:
            Force explicit GC execution regardless of threshold.

        Returns
        -------
        bool: True if cleanup was executed.
        """
        if not self.config.enable_memory_cleanup and not force:
            return False

        should_gc = force
        if resource_monitor and not should_gc:
            should_gc = resource_monitor.check_memory_threshold(self.config.max_memory_threshold_mb)

        if should_gc:
            before_rss = resource_monitor.get_current_rss_mb() if resource_monitor else 0.0
            gc.collect()
            after_rss = resource_monitor.get_current_rss_mb() if resource_monitor else 0.0
            freed_mb = max(0.0, before_rss - after_rss)
            logger.info(
                f"[RepositoryOptimizer] Memory threshold reached ({before_rss:.1f}MB). "
                f"Executed GC: Freed {freed_mb:.1f}MB (Current: {after_rss:.1f}MB)"
            )
            return True

        return False
