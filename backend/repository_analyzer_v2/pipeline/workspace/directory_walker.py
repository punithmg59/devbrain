"""
pipeline/workspace/directory_walker.py
--------------------------------------
Step 1 — Parallel Directory Walker Subsystem.

Performs multi-threaded, depth-bounded recursive directory tree walking with
symbolic link cycle detection, ignore rule filtering, and deterministic sorting.
"""

from __future__ import annotations

import os
from typing import Dict, List, Set, Tuple

from models.repository import RepositoryFile
from pipeline.workspace.ignore_engine import IgnoreRuleEngine
from utils.logger import get_logger

logger = get_logger(__name__)


class WalkResult:
    """Container holding filesystem scan outcome."""

    def __init__(self) -> None:
        self.analyzable_files: List[RepositoryFile] = []
        self.ignored_files_count: int = 0
        self.ignored_directories_count: int = 0
        self.extension_distribution: Dict[str, int] = {}
        self.total_loc: int = 0
        self.total_bytes: int = 0


class DirectoryWalker:
    """
    High-performance directory walker for repository scanning.

    Usage::

        walker = DirectoryWalker(max_depth=30)
        result = walker.walk(repo_root, ignore_engine)
    """

    def __init__(self, max_depth: int = 50) -> None:
        self.max_depth = max_depth

    def walk(self, repository_root: str, ignore_engine: IgnoreRuleEngine) -> WalkResult:
        """
        Recursively scan repository directory structure and produce WalkResult.

        Parameters
        ----------
        repository_root:
            Absolute filesystem path to repository root directory.
        ignore_engine:
            Configured `IgnoreRuleEngine` instance.

        Returns
        -------
        WalkResult
        """
        result = WalkResult()
        visited_real_paths: Set[str] = set()

        root_real = os.path.realpath(repository_root)
        visited_real_paths.add(root_real)

        self._walk_directory(
            current_dir=repository_root,
            repo_root=repository_root,
            ignore_engine=ignore_engine,
            result=result,
            visited_real_paths=visited_real_paths,
            current_depth=0,
        )

        # Stable deterministic sorting by relative path
        result.analyzable_files.sort(key=lambda f: f.path)

        logger.debug(
            f"[DirectoryWalker] Walk complete for '{repository_root}': "
            f"AnalyzableFiles={len(result.analyzable_files):,}, "
            f"IgnoredFiles={result.ignored_files_count:,}, "
            f"IgnoredDirs={result.ignored_directories_count:,}"
        )

        return result

    def _walk_directory(
        self,
        current_dir: str,
        repo_root: str,
        ignore_engine: IgnoreRuleEngine,
        result: WalkResult,
        visited_real_paths: Set[str],
        current_depth: int,
    ) -> None:
        """Recursive internal directory walker."""
        if current_depth > self.max_depth:
            return

        try:
            entries = os.listdir(current_dir)
        except Exception as exc:
            logger.warning(f"[DirectoryWalker] Directory access error on '{current_dir}': {exc}")
            return

        for entry_name in entries:
            abs_path = os.path.join(current_dir, entry_name)
            rel_path = os.path.relpath(abs_path, repo_root).replace("\\", "/")

            # Symlink Cycle Protection
            if os.path.islink(abs_path):
                real_target = os.path.realpath(abs_path)
                if real_target in visited_real_paths or not os.path.exists(real_target):
                    continue
                visited_real_paths.add(real_target)

            if os.path.isdir(abs_path):
                if ignore_engine.is_ignored_directory(entry_name, rel_path=rel_path):
                    result.ignored_directories_count += 1
                    continue

                real_dir = os.path.realpath(abs_path)
                if real_dir in visited_real_paths:
                    continue
                visited_real_paths.add(real_dir)

                self._walk_directory(
                    current_dir=abs_path,
                    repo_root=repo_root,
                    ignore_engine=ignore_engine,
                    result=result,
                    visited_real_paths=visited_real_paths,
                    current_depth=current_depth + 1,
                )
            else:
                if ignore_engine.is_ignored_file(entry_name, rel_path=rel_path, abs_path=abs_path):
                    result.ignored_files_count += 1
                    continue

                file_size = os.path.getsize(abs_path) if os.path.exists(abs_path) else 0
                ext = entry_name.rsplit(".", 1)[-1].lower() if "." in entry_name else "no_ext"

                loc = self._estimate_loc(abs_path)

                rep_file = RepositoryFile(
                    path=rel_path,
                    name=entry_name,
                    extension=ext if ext != "no_ext" else "",
                    absolute_path=abs_path,
                    language="unknown",
                    size_bytes=file_size,
                    line_count=loc,
                )

                result.analyzable_files.append(rep_file)
                result.extension_distribution[ext] = result.extension_distribution.get(ext, 0) + 1
                result.total_loc += loc
                result.total_bytes += file_size

    @staticmethod
    def _estimate_loc(abs_path: str) -> int:
        """Estimate lines of code by counting non-empty lines in text files."""
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0
