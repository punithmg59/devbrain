"""
plugins/parser_plugin.py
------------------------
Phase 3.4 — Parser SDK & Abstract `ParserPlugin` Base Class.

Defines the parser-independent `ParserPlugin` Abstract Base Class (ABC)
and the `DummyParserPlugin` reference implementation.

Design Principles
-----------------
- **Parser-Independent SDK**: Decoupled from native parser engines (Tree-sitter, ANTLR,
  Babel, etc.). Provides a unified contract for all language parsing plugins.
- **Strict Lifecyle Management**: `initialize()`, `parse()`, `validate()`, `shutdown()`, and
  `health()` methods guarantee predictable plugin resource management.
- **Rich Operational Contracts**: Every parser plugin exposes `language`, `version`,
  and `capabilities` specifications via strongly-typed models.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from core.execution_context import ExecutionContext
from models.ast import ASTNode, ASTRoot, NodeLocation, NodeRange, NodeType
from models.health import ComponentHealth, HealthStatus
from models.job import AnalysisJob
from models.parser import (
    ParserCapabilities,
    ParserLanguage,
    ParserMetadata,
    ParserOptions,
    ParserResult,
    ParserStatistics,
    ParserStatus,
    ParserVersion,
)
from utils.exceptions import ErrorCode, ParserError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract ParserPlugin Base Class
# ---------------------------------------------------------------------------

class ParserPlugin(ABC):
    """
    Abstract Base Class (ABC) for all language-specific parser plugins in DevBrain.
    """

    def __init__(self) -> None:
        self._is_initialized: bool = False

    @property
    def is_initialized(self) -> bool:
        """True if plugin has completed initialisation."""
        return self._is_initialized

    @property
    @abstractmethod
    def language(self) -> ParserLanguage:
        """Primary programming language supported by this parser plugin."""
        pass

    @property
    @abstractmethod
    def version(self) -> ParserVersion:
        """Parser engine and grammar version specifications."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> ParserCapabilities:
        """Feature capabilities supported by this parser plugin."""
        pass

    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the parser plugin with configuration settings.

        Allocates grammar rules, native libraries, or engine resources.
        Must set `self._is_initialized = True`.
        """
        pass

    @abstractmethod
    def parse(
        self,
        job: AnalysisJob,
        context: ExecutionContext,
        options: Optional[ParserOptions] = None,
    ) -> ParserResult:
        """
        Parse a source file dispatched via `AnalysisJob` and `ExecutionContext`.

        :param job: The AnalysisJob carrying the source file reference.
        :param context: The worker ExecutionContext.
        :param options: Optional parsing options overriding defaults.
        :return: ParserResult object containing status, metadata, statistics, and AST.
        """
        pass

    @abstractmethod
    def validate(self, content: str) -> bool:
        """
        Validate whether source code content is syntactically valid.

        :param content: Source code string to check.
        :return: True if syntactically valid, False if syntax errors detected.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Release all allocated parser engine resources, file handles, or subprocesses.

        Must set `self._is_initialized = False`.
        """
        pass

    def health(self) -> ComponentHealth:
        """
        Check and return the health status of this parser plugin.
        """
        status = HealthStatus.HEALTHY if self._is_initialized else HealthStatus.UNHEALTHY
        msg = f"Parser plugin '{self.language.value}' is {'initialized' if self._is_initialized else 'not initialized'}."
        return ComponentHealth(
            name=f"ParserPlugin:{self.language.value}",
            status=status,
            message=msg,
            details={
                "language": self.language.value,
                "version": self.version.semver,
                "initialized": self._is_initialized,
            },
        )


# ---------------------------------------------------------------------------
# DummyParserPlugin Reference Implementation
# ---------------------------------------------------------------------------

class DummyParserPlugin(ParserPlugin):
    """
    Reference / Mock implementation of `ParserPlugin` for testing and fallback parsing.
    """

    def __init__(
        self,
        target_language: ParserLanguage = ParserLanguage.PYTHON,
        semver: str = "1.0.0-dummy",
    ) -> None:
        super().__init__()
        self._target_language: ParserLanguage = target_language
        self._version: ParserVersion = ParserVersion(
            semver=semver,
            grammar_version="dummy-v1",
            abi_version=1,
        )
        self._capabilities: ParserCapabilities = ParserCapabilities(
            supports_ast=True,
            supports_cst=False,
            supports_incremental=False,
            supports_symbol_extraction=True,
            supports_import_extraction=True,
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
        logger.debug(f"[DummyParserPlugin:{self.language.value}] Initialized")

    def parse(
        self,
        job: AnalysisJob,
        context: ExecutionContext,
        options: Optional[ParserOptions] = None,
    ) -> ParserResult:
        if not self._is_initialized:
            raise ParserError(
                f"Parser plugin '{self.language.value}' must be initialized before parse().",
                code=ErrorCode.PLUGIN_INIT_FAILED,
            )

        start_time = time.monotonic()
        opts = options or ParserOptions()

        # Build dummy AST
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

        duration_ms = (time.monotonic() - start_time) * 1000.0

        metadata = ParserMetadata(
            parser_name=f"dummy-parser-{self.language.value}",
            language=self.language,
            version=self.version,
            capabilities=self.capabilities,
            file_hash=job.file.hash_sha256,
        )

        stats = ParserStatistics(
            duration_ms=duration_ms,
            bytes_parsed=job.file.size_bytes,
            lines_parsed=job.file.line_count,
            node_count=ast_root.total_nodes,
        )

        result = ParserResult(
            job_id=job.job_id,
            file_path=job.file.path,
            language=self.language,
            status=ParserStatus.SUCCESS,
            statistics=stats,
            metadata=metadata,
            ast_root=ast_root.model_dump(),
        )

        logger.debug(f"[DummyParserPlugin:{self.language.value}] Parsed file '{job.file.path}'")
        return result

    def validate(self, content: str) -> bool:
        if "SYNTAX_ERROR" in content:
            return False
        return True

    def shutdown(self) -> None:
        self._is_initialized = False
        logger.debug(f"[DummyParserPlugin:{self.language.value}] Shutdown complete")
