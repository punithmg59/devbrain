"""
plugins/python/builder_plugin.py
---------------------------------
Step 2 — Python Builder Plugin Implementation.

Ingests a `RepositoryWorkspace` manifest produced by Step 1, filters Python source files,
executes AST parsing, records parser diagnostics, and returns immutable `ParserResult` objects.

CRITICAL INVARIANTS:
-------------------
- Does NOT re-scan the repository or walk directories.
- Uses `RepositoryWorkspace` exactly as provided.
- Extracts strictly syntactic AST structures (Module, Classes, Functions, AsyncFunctions,
  Decorators, Arguments, Annotations, Control Flow, Expressions, Docstrings, NodeRange positions).
- Does NOT build Symbol Tables, Graph Nodes, Edges, Namespaces, or persist to PostgreSQL.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Generator, List, Optional

from core.execution_context import ExecutionContext
from models.job import AnalysisJob
from models.parser import ParserResult, ParserStatus
from models.repository import RepositoryFile
from pipeline.workspace.models import RepositoryWorkspace
from plugins.builder_plugin import BuilderPlugin, BuilderPluginCapabilities, BuilderPluginMetadata
from plugins.python.python_parser_plugin import PythonParserPlugin
from utils.logger import get_logger

logger = get_logger(__name__)


class PythonBuilderPlugin(BuilderPlugin):
    """
    Python Builder Plugin for DevBrain Dependency Graph Platform.

    Usage::

        plugin = PythonBuilderPlugin()
        plugin.initialize()
        results = plugin.execute(workspace)
    """

    def __init__(self) -> None:
        self._meta = BuilderPluginMetadata(
            plugin_id="devbrain.plugin.python",
            name="Python Builder Plugin",
            version="2.5.0",
            target_language="python",
            supported_extensions=["py", "pyi"],
            capabilities=BuilderPluginCapabilities(
                syntax_ast=True,
                error_recovery=True,
                comments=True,
                docstrings=True,
                type_annotations=True,
            ),
        )
        self._parser_plugin = PythonParserPlugin()
        self._is_initialized = False

    @property
    def metadata(self) -> BuilderPluginMetadata:
        return self._meta

    @property
    def target_language(self) -> str:
        return "python"

    def initialize(self, configuration: Optional[Dict[str, Any]] = None) -> None:
        """Initialize Python parser plugin engine."""
        if not self._is_initialized:
            self._parser_plugin.initialize()
            self._is_initialized = True
            logger.info("[PythonBuilderPlugin] Initialized Python Builder Plugin engine")

    def execute(self, workspace: RepositoryWorkspace) -> List[ParserResult]:
        """
        Ingest `RepositoryWorkspace` manifest and execute AST parsing for Python source files.

        Parameters
        ----------
        workspace:
            `RepositoryWorkspace` object from Step 1.

        Returns
        -------
        List[ParserResult]
            List of `ParserResult` objects sorted by file path.
        """
        if not self._is_initialized:
            self.initialize()

        logger.info(
            f"[PythonBuilderPlugin] Executing Python Builder Plugin on workspace '{workspace.repository_name}' "
            f"({len(workspace.analyzable_files):,} candidate files)"
        )
        start_time = time.perf_counter()

        python_files = self._filter_python_files(workspace.analyzable_files)
        results: List[ParserResult] = []

        for rep_file in python_files:
            p_res = self._parse_single_file(rep_file, workspace)
            results.append(p_res)

        # Stable deterministic sorting by file relative path
        results.sort(key=lambda r: r.file_path)

        dt_ms = (time.perf_counter() - start_time) * 1000.0
        success_count = sum(1 for r in results if r.status == ParserStatus.SUCCESS)

        logger.info(
            f"[PythonBuilderPlugin] Completed execution for '{workspace.repository_name}': "
            f"Parsed={len(results):,}, Success={success_count:,}, Duration={dt_ms:.2f}ms"
        )

        return results

    def execute_streaming(
        self,
        workspace: RepositoryWorkspace,
    ) -> Generator[ParserResult, None, None]:
        """
        Stream `ParserResult` items iteratively for large repositories (100,000+ files).
        """
        if not self._is_initialized:
            self.initialize()

        python_files = self._filter_python_files(workspace.analyzable_files)
        for rep_file in python_files:
            yield self._parse_single_file(rep_file, workspace)

    def _filter_python_files(self, files: List[RepositoryFile]) -> List[RepositoryFile]:
        """Filter analyzable source files for Python language or py/pyi extensions."""
        return [
            f for f in files
            if f.language == "python" or f.extension.lower() in ("py", "pyi")
        ]

    def _parse_single_file(
        self,
        rep_file: RepositoryFile,
        workspace: RepositoryWorkspace,
    ) -> ParserResult:
        """Parse a single RepositoryFile into a ParserResult."""
        source_code = rep_file.content

        # Load file content from disk if not present in manifest
        if source_code is None and rep_file.absolute_path and os.path.exists(rep_file.absolute_path):
            try:
                with open(rep_file.absolute_path, "r", encoding="utf-8", errors="replace") as f:
                    source_code = f.read()
            except Exception as exc:
                logger.warning(f"[PythonBuilderPlugin] Failed to read '{rep_file.path}': {exc}")
                source_code = ""

        if source_code is None:
            source_code = ""

        file_obj = RepositoryFile(
            path=rep_file.path,
            name=rep_file.name or os.path.basename(rep_file.path),
            extension=rep_file.extension or "py",
            absolute_path=rep_file.absolute_path,
            language="python",
            size_bytes=len(source_code.encode("utf-8", errors="replace")),
            line_count=source_code.count("\n") + 1,
            content=source_code,
        )

        job = AnalysisJob(
            repository_id=workspace.repository_name,
            file=file_obj,
            language="python",
        )

        context = ExecutionContext(job=job, worker=None, pipeline_context=None)

        try:
            return self._parser_plugin.parse(job, context)
        except Exception as exc:
            logger.error(f"[PythonBuilderPlugin] Parser crash on '{rep_file.path}': {exc}")
            # Fault isolation: return INTERNAL_ERROR ParserResult instead of crashing
            return self._parser_plugin._error_result(
                job=job,
                status=ParserStatus.INTERNAL_ERROR,
                message=f"Parser unhandled exception: {exc}",
            )
