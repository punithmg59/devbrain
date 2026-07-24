"""
analysis/benchmark/repository_suite.py
---------------------------------------
Phase 4.8.5 — Repository Benchmark Suite Registry.

Manages target repository configurations across size categories (Small, Medium, Large, Enterprise)
for automated benchmark execution.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from models.benchmark_models import RepositoryBenchmarkTarget, RepositorySizeCategory
from utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryBenchmarkSuite:
    """
    Registry container for target benchmark repositories.

    Usage::

        suite = RepositoryBenchmarkSuite.get_default_suite()
        targets = suite.get_targets()
    """

    def __init__(self) -> None:
        self._targets: Dict[str, RepositoryBenchmarkTarget] = {}

    def add_target(self, target: RepositoryBenchmarkTarget) -> None:
        """Add or register a benchmark target repository."""
        self._targets[target.name] = target
        logger.debug(f"[RepositoryBenchmarkSuite] Registered target '{target.name}' ({target.category.value}) at '{target.path}'")

    def get_targets(self) -> List[RepositoryBenchmarkTarget]:
        """Return list of all registered benchmark target repositories."""
        return list(self._targets.values())

    def get_target_by_name(self, name: str) -> Optional[RepositoryBenchmarkTarget]:
        """Get target repository by name."""
        return self._targets.get(name)

    @classmethod
    def get_default_suite(cls, workspace_root: str = "d:\\devbrain") -> RepositoryBenchmarkSuite:
        """
        Construct and return the default DevBrain benchmark suite containing real-world repositories.
        """
        suite = cls()

        # Target 1: FastAPI (Large / Enterprise-scale repository)
        fastapi_path = os.path.join(workspace_root, "fastapi")
        if os.path.exists(fastapi_path):
            suite.add_target(
                RepositoryBenchmarkTarget(
                    name="FastAPI",
                    path=fastapi_path,
                    category=RepositorySizeCategory.LARGE,
                    description="FastAPI Web Framework (1,127 Python files / 111,345 LOC)",
                )
            )

        # Target 2: Trading_bot (Medium / Multi-module repository)
        trading_bot_path = os.path.join(workspace_root, "Trading_bot")
        if os.path.exists(trading_bot_path):
            suite.add_target(
                RepositoryBenchmarkTarget(
                    name="Trading_bot",
                    path=trading_bot_path,
                    category=RepositorySizeCategory.MEDIUM,
                    description="Algorithmic Trading Bot Framework",
                )
            )

        return suite
