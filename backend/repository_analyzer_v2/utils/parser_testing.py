"""
utils/parser_testing.py
------------------------
Phase 3.9 — Parser Testing Framework.

Provides test parser plugins, mock fixtures, invalid plugin generators, and test harness
utilities for benchmarking, stress testing, concurrency validation, and fault isolation testing.

Components
----------
- **ConfigurableMockParserPlugin**: Mock parser with customizable status, AST, errors, and statistics.
- **BrokenParserPlugin**: Simulated failing parser that raises configurable uncaught exceptions.
- **SlowParserPlugin**: Simulated slow parser with configurable execution delays.
- **TimeoutParserPlugin**: Parser designed to exceed execution timeouts or trigger cancellation.
- **InvalidParserPlugin**: Non-compliant plugin implementation for contract validation testing.
- **ParserTestHarness**: Helper utility for stress testing, concurrency benchmarking, and verification.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Type, Union

from core.execution_context import ExecutionContext
from core.parser_manager import ParserManager
from core.worker_pool import Worker
from models.ast import ASTNode, ASTRoot, NodeLocation, NodeRange, NodeType
from models.job import AnalysisJob
from models.parser import (
    ParserCapabilities,
    ParserError,
    ParserLanguage,
    ParserMetadata,
    ParserOptions,
    ParserResult,
    ParserStatistics,
    ParserStatus,
    ParserVersion,
    ParserWarning,
)
from models.repository import Repository, RepositoryFile
from pipeline.context import PipelineContext
from plugins.parser_plugin import ParserPlugin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Test Parser Plugins
# ---------------------------------------------------------------------------

class ConfigurableMockParserPlugin(ParserPlugin):
    """
    Mock parser plugin with fully configurable result outputs.
    """

    def __init__(
        self,
        target_language: ParserLanguage = ParserLanguage.PYTHON,
        return_status: ParserStatus = ParserStatus.SUCCESS,
        errors: Optional[List[ParserError]] = None,
        warnings: Optional[List[ParserWarning]] = None,
        semver: str = "1.0.0-mock",
    ) -> None:
        super().__init__()
        self._target_language: ParserLanguage = target_language
        self._return_status: ParserStatus = return_status
        self._errors: List[ParserError] = errors or []
        self._warnings: List[ParserWarning] = warnings or []
        self._version: ParserVersion = ParserVersion(semver=semver)
        self._capabilities: ParserCapabilities = ParserCapabilities(
            supports_ast=True,
            supports_symbol_extraction=True,
        )

    @property
    def language(self) -> ParserLanguage:
        return self._target_language

    @property
    def version(self) -> ParserVersion:
        return self._version

    @property
    def capabilities(self) -> ParserCapabilities:
        return self._capabilities

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._is_initialized = True

    def parse(
        self,
        job: AnalysisJob,
        context: ExecutionContext,
        options: Optional[ParserOptions] = None,
    ) -> ParserResult:
        if not self._is_initialized:
            raise RuntimeError("Mock parser not initialized.")

        root_node = ASTNode(
            type=NodeType.MODULE,
            name=job.file.name,
            range=NodeRange(
                start=NodeLocation(line=1, column=0),
                end=NodeLocation(line=max(1, job.file.line_count), column=10),
            ),
        )
        ast_root = ASTRoot(
            file_path=job.file.path,
            language=self.language.value,
            root_node=root_node,
        )
        ast_root.recalculate_metrics()

        return ParserResult(
            job_id=job.job_id,
            file_path=job.file.path,
            language=self.language,
            status=self._return_status,
            errors=self._errors,
            warnings=self._warnings,
            statistics=ParserStatistics(
                duration_ms=1.0,
                bytes_parsed=job.file.size_bytes,
                lines_parsed=job.file.line_count,
                node_count=ast_root.total_nodes,
            ),
            metadata=ParserMetadata(
                parser_name=f"mock-parser-{self.language.value}",
                language=self.language,
                version=self.version,
            ),
            ast_root=ast_root.model_dump(),
        )

    def validate(self, content: str) -> bool:
        return True

    def shutdown(self) -> None:
        self._is_initialized = False


class BrokenParserPlugin(ParserPlugin):
    """
    Parser plugin that raises an uncaught exception during `parse()`.
    """

    def __init__(
        self,
        target_language: ParserLanguage = ParserLanguage.PYTHON,
        exception_factory: Optional[Type[Exception]] = None,
    ) -> None:
        super().__init__()
        self._target_language: ParserLanguage = target_language
        self._exception_factory: Type[Exception] = exception_factory or RuntimeError
        self._version: ParserVersion = ParserVersion(semver="1.0.0-broken")
        self._capabilities: ParserCapabilities = ParserCapabilities()

    @property
    def language(self) -> ParserLanguage:
        return self._target_language

    @property
    def version(self) -> ParserVersion:
        return self._version

    @property
    def capabilities(self) -> ParserCapabilities:
        return self._capabilities

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._is_initialized = True

    def parse(
        self,
        job: AnalysisJob,
        context: ExecutionContext,
        options: Optional[ParserOptions] = None,
    ) -> ParserResult:
        raise self._exception_factory(f"Simulated crash in BrokenParserPlugin for '{job.file.path}'!")

    def validate(self, content: str) -> bool:
        return False

    def shutdown(self) -> None:
        self._is_initialized = False


class SlowParserPlugin(ParserPlugin):
    """
    Parser plugin that introduces an artificial execution delay during `parse()`.
    """

    def __init__(
        self,
        target_language: ParserLanguage = ParserLanguage.PYTHON,
        delay_seconds: float = 0.1,
    ) -> None:
        super().__init__()
        self._target_language: ParserLanguage = target_language
        self.delay_seconds: float = delay_seconds
        self._version: ParserVersion = ParserVersion(semver="1.0.0-slow")
        self._capabilities: ParserCapabilities = ParserCapabilities()

    @property
    def language(self) -> ParserLanguage:
        return self._target_language

    @property
    def version(self) -> ParserVersion:
        return self._version

    @property
    def capabilities(self) -> ParserCapabilities:
        return self._capabilities

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._is_initialized = True

    def parse(
        self,
        job: AnalysisJob,
        context: ExecutionContext,
        options: Optional[ParserOptions] = None,
    ) -> ParserResult:
        time.sleep(self.delay_seconds)
        return ParserResult(
            job_id=job.job_id,
            file_path=job.file.path,
            language=self.language,
            status=ParserStatus.SUCCESS,
            statistics=ParserStatistics(duration_ms=self.delay_seconds * 1000.0),
            metadata=ParserMetadata(
                parser_name="slow-parser",
                language=self.language,
                version=self.version,
            ),
        )

    def validate(self, content: str) -> bool:
        return True

    def shutdown(self) -> None:
        self._is_initialized = False


class TimeoutParserPlugin(ParserPlugin):
    """
    Parser plugin that sleeps for an extended duration to trigger timeouts or cancellation.
    """

    def __init__(
        self,
        target_language: ParserLanguage = ParserLanguage.PYTHON,
        sleep_duration_seconds: float = 5.0,
    ) -> None:
        super().__init__()
        self._target_language: ParserLanguage = target_language
        self.sleep_duration_seconds: float = sleep_duration_seconds
        self._version: ParserVersion = ParserVersion(semver="1.0.0-timeout")
        self._capabilities: ParserCapabilities = ParserCapabilities()

    @property
    def language(self) -> ParserLanguage:
        return self._target_language

    @property
    def version(self) -> ParserVersion:
        return self._version

    @property
    def capabilities(self) -> ParserCapabilities:
        return self._capabilities

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._is_initialized = True

    def parse(
        self,
        job: AnalysisJob,
        context: ExecutionContext,
        options: Optional[ParserOptions] = None,
    ) -> ParserResult:
        step = 0.05
        elapsed = 0.0
        while elapsed < self.sleep_duration_seconds:
            if context.cancellation_token and context.cancellation_token.is_cancelled:
                raise asyncio.CancelledError("Parse execution cancelled by context token.")
            time.sleep(step)
            elapsed += step

        return ParserResult(
            job_id=job.job_id,
            file_path=job.file.path,
            language=self.language,
            status=ParserStatus.TIMEOUT,
        )

    def validate(self, content: str) -> bool:
        return True

    def shutdown(self) -> None:
        self._is_initialized = False


class InvalidParserPlugin:
    """
    Non-compliant object that does NOT inherit from `ParserPlugin` ABC.
    """
    pass


# ---------------------------------------------------------------------------
# Parser Test Harness Utility
# ---------------------------------------------------------------------------

class ParserTestHarness:
    """
    Utility harness for constructing test jobs, context objects, stress testing,
    and concurrent execution benchmarks.
    """

    @staticmethod
    def create_job(
        path: str = "src/test_file.py",
        language: str = "python",
        size_bytes: int = 100,
        line_count: int = 10,
        repo_id: str = "repo-harness",
    ) -> AnalysisJob:
        file = RepositoryFile(
            path=path,
            name=path.rsplit("/", 1)[-1],
            extension=path.rsplit(".", 1)[-1],
            language=language,
            size_bytes=size_bytes,
            line_count=line_count,
        )
        return AnalysisJob.from_repository_file(repository_id=repo_id, file=file)

    @staticmethod
    def create_context(job: AnalysisJob, run_id: str = "run-harness") -> ExecutionContext:
        worker = Worker(worker_id="w-harness-1")
        repo = Repository(id=job.repository_id, url="/tmp", name="harness-repo")
        pipeline_ctx = PipelineContext(run_id=run_id, repository=repo)
        return ExecutionContext(job=job, worker=worker, pipeline_context=pipeline_ctx)

    @staticmethod
    async def run_stress_test(
        manager: ParserManager,
        job_count: int = 100,
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        Execute `job_count` jobs sequentially or concurrently against `manager`.
        """
        start = time.monotonic()
        results: List[ParserResult] = []

        for i in range(job_count):
            job = ParserTestHarness.create_job(
                path=f"src/file_{i}.py",
                language=language,
            )
            ctx = ParserTestHarness.create_context(job, run_id="stress-run")
            res = await manager.execute_parser(job, ctx)
            results.append(res)

        elapsed = time.monotonic() - start
        successes = sum(1 for r in results if r.status == ParserStatus.SUCCESS)

        return {
            "job_count": job_count,
            "completed": len(results),
            "successes": successes,
            "elapsed_seconds": round(elapsed, 4),
            "throughput_jobs_per_sec": round(job_count / max(0.0001, elapsed), 2),
        }
