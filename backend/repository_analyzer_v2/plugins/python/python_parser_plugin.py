"""
plugins/python/python_parser_plugin.py
---------------------------------------
Phase 4.2 — Production Python Parser Plugin.

Implements the ``ParserPlugin`` ABC for the Python language using the
``TreeSitterEngine`` as the parse backend and ``PythonASTConverter`` for
tree-to-AST translation.

Pipeline Position
-----------------
::

    RepositoryFile
      └─► ParserManager.execute_parser()
            └─► PythonParserPlugin.parse()
                  ├─► TreeSitterEngine.parse()          # raw parse tree
                  ├─► PythonASTConverter.convert()      # DevBrain AST
                  ├─► ParserValidator.validate_result()  # validation
                  └─► ParserResult                      # return to caller

Key Design Decisions
---------------------
1. **TreeSitterEngine injected at initialize-time**: The plugin does not
   construct its own engine; it receives a shared ``TreeSitterEngine``
   instance from the ``ParserManager``. This avoids double grammar-loading
   and makes the plugin unit-testable with a mock engine.

2. **Language-key routing**: Python source maps to grammar key ``"python"``.
   Files with ``.pyi`` (stub) extension are also accepted.

3. **Never crash**: All exceptions in ``parse()`` are caught and returned as
   ``ParserResult(status=INTERNAL_ERROR)`` with diagnostic error records.

4. **Encoding resilience**: If the raw file bytes cannot be decoded as UTF-8,
   the plugin falls back to ``latin-1`` (byte-transparent) before reporting an
   encoding warning.

5. **Automatic validation**: Every successful ``ParserResult`` passes through
   ``ParserValidator.validate_result()``; warnings from validation are appended
   to the result without blocking delivery.

6. **Source hash**: SHA-256 of the raw source bytes is embedded in
   ``ParserMetadata.file_hash`` for change-detection and caching pipelines.
"""

from __future__ import annotations

import hashlib
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from core.execution_context import ExecutionContext
from core.parser_validator import ParserValidator
from core.tree_sitter_engine import TreeSitterEngine
from models.ast import ASTRoot
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
from models.parser import ParserError as ModelParserError
from models.parser import ParserWarning as ModelParserWarning
from models.tree_sitter_models import ParseTree
from plugins.parser_plugin import ParserPlugin
from plugins.python.ast_converter import PythonASTConverter
from plugins.python.native_ast_converter import convert_python_native_ast
from plugins.python.semantic_extractor import PythonSemanticExtractor
from utils.exceptions import ErrorCode, ParserError as EngineParserError
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Plugin Constants
# ---------------------------------------------------------------------------

_PLUGIN_NAME = "tree-sitter-python"
_PLUGIN_SEMVER = "4.2.0"
_GRAMMAR_KEY = "python"
_SUPPORTED_EXTENSIONS = frozenset({"py", "pyi"})

# tree-sitter-python package version — fetched at runtime to embed in metadata
def _get_ts_python_version() -> str:
    try:
        import tree_sitter_python
        return getattr(tree_sitter_python, "__version__", "unknown")
    except ImportError:
        return "unknown"


# ---------------------------------------------------------------------------
# PythonParserPlugin
# ---------------------------------------------------------------------------

class PythonParserPlugin(ParserPlugin):
    """
    Production-quality Python language parser plugin for DevBrain V2.

    Implements the ``ParserPlugin`` ABC contract using:

    - ``TreeSitterEngine`` as the parse backend (grammar key ``"python"``)
    - ``PythonASTConverter`` for parse-tree → DevBrain AST translation
    - ``ParserValidator`` for automatic output validation

    Thread Safety
    -------------
    ``PythonParserPlugin`` is thread-safe. Its internal state (``_is_initialized``,
    ``_engine``) is written once during ``initialize()`` under a ``threading.Lock``
    and is thereafter read-only during concurrent ``parse()`` calls.

    Dependency Injection
    --------------------
    An existing ``TreeSitterEngine`` can be injected via the constructor to avoid
    re-loading grammars when the ``ParserManager`` already owns an engine.
    If not injected, a private engine is created and owned by this plugin.
    """

    def __init__(
        self,
        engine: Optional[TreeSitterEngine] = None,
        validator: Optional[ParserValidator] = None,
    ) -> None:
        """
        Parameters
        ----------
        engine:
            Optional shared ``TreeSitterEngine``.  If ``None``, the plugin
            creates and owns its own engine.
        validator:
            Optional ``ParserValidator`` instance.  Defaults to a fresh instance
            with default requirements.
        """
        super().__init__()
        self._engine: Optional[TreeSitterEngine] = engine
        self._owns_engine: bool = engine is None
        self._validator: ParserValidator = validator or ParserValidator()
        self._init_lock: threading.Lock = threading.Lock()
        self._ts_python_version: str = _get_ts_python_version()

        self._semantic_extractor: PythonSemanticExtractor = PythonSemanticExtractor()
        # Benchmarking accumulators (all protected by GIL for int/float)
        self._total_parses: int = 0
        self._total_parse_ms: float = 0.0
        self._total_ast_nodes: int = 0

    # ------------------------------------------------------------------
    # ParserPlugin ABC Properties
    # ------------------------------------------------------------------

    @property
    def language(self) -> ParserLanguage:
        """Primary language: Python."""
        return ParserLanguage.PYTHON

    @property
    def version(self) -> ParserVersion:
        """Plugin and grammar version info."""
        abi = 0
        if self._engine and self._engine.is_language_loaded(_GRAMMAR_KEY):
            gv = self._engine.get_grammar_version(_GRAMMAR_KEY)
            abi = gv.abi_version if gv else 0

        return ParserVersion(
            semver=_PLUGIN_SEMVER,
            grammar_version=self._ts_python_version,
            abi_version=max(1, abi) if abi > 0 else 1,
        )

    @property
    def capabilities(self) -> ParserCapabilities:
        """Full capability set for the Python parser."""
        return ParserCapabilities(
            supports_ast=True,
            supports_cst=False,
            supports_incremental=False,
            supports_symbol_extraction=True,
            supports_import_extraction=True,
            supports_docstring_extraction=True,
            supports_error_recovery=True,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the plugin: load Python grammar via the ``TreeSitterEngine``.

        If an engine was injected and already has the Python grammar loaded,
        this method is a no-op for the grammar step.

        Parameters
        ----------
        config:
            Optional configuration dict.  Recognized keys:

            - ``"max_ast_depth"`` (int): Maximum AST conversion depth (default 200).

        Raises
        ------
        RuntimeError
            If grammar loading fails and the engine cannot serve Python parses.
        """
        with self._init_lock:
            if self._is_initialized:
                logger.debug("[PythonParserPlugin] Already initialized — skipping.")
                return

            cfg = config or {}
            max_ast_depth = int(cfg.get("max_ast_depth", 200))

            # Obtain or create engine
            if self._engine is None:
                self._engine = TreeSitterEngine()

            # Load Python grammar if not already loaded
            if not self._engine._is_initialized or not self._engine.is_language_loaded(_GRAMMAR_KEY):
                try:
                    self._engine.initialize([ParserLanguage.PYTHON])
                except Exception as exc:
                    logger.warning(
                        f"[PythonParserPlugin] TreeSitterEngine failed to initialize: {exc}. "
                        "Falling back to native Python ast module."
                    )

            self._max_ast_depth: int = max_ast_depth
            self._is_initialized = True
            logger.info(
                f"[PythonParserPlugin] Initialized (grammar={self._ts_python_version}, "
                f"max_depth={max_ast_depth})"
            )

    def shutdown(self) -> None:
        """
        Shutdown the plugin.

        If the plugin owns its engine (created internally), the engine is
        shut down and released.  If the engine was injected, it is left alone.
        """
        with self._init_lock:
            if not self._is_initialized:
                return
            if self._owns_engine and self._engine is not None:
                try:
                    self._engine.shutdown()
                    logger.info("[PythonParserPlugin] Owned TreeSitterEngine shut down.")
                except Exception as exc:
                    logger.warning(f"[PythonParserPlugin] Engine shutdown error: {exc}")
            self._engine = None
            self._is_initialized = False
            logger.info("[PythonParserPlugin] Shutdown complete.")

    def health(self) -> ComponentHealth:
        """Return component health status."""
        if not self._is_initialized or self._engine is None:
            return ComponentHealth(
                name=f"ParserPlugin:{ParserLanguage.PYTHON.value}",
                status=HealthStatus.UNHEALTHY,
                message="PythonParserPlugin is not initialized.",
                details={"initialized": False},
            )

        grammar_ok = self._engine.is_language_loaded(_GRAMMAR_KEY) if self._engine else False
        status = HealthStatus.HEALTHY if self._is_initialized else HealthStatus.UNHEALTHY
        return ComponentHealth(
            name=f"ParserPlugin:{ParserLanguage.PYTHON.value}",
            status=status,
            message=(
                f"PythonParserPlugin {'ready' if self._is_initialized else 'not initialized'}. "
                f"Total parses: {self._total_parses}"
            ),
            details={
                "initialized": True,
                "grammar_loaded": grammar_ok,
                "total_parses": self._total_parses,
                "avg_parse_ms": round(
                    self._total_parse_ms / max(1, self._total_parses), 2
                ),
                "grammar_version": self._ts_python_version,
                "plugin_version": _PLUGIN_SEMVER,
            },
        )

    # ------------------------------------------------------------------
    # Validation shortcut
    # ------------------------------------------------------------------

    def validate(self, content: str) -> bool:
        if not self._is_initialized:
            return False
        try:
            source = content.encode("utf-8", errors="replace")
            if self._engine and self._engine.is_language_loaded(_GRAMMAR_KEY):
                tree = self._engine.parse(_GRAMMAR_KEY, source, "<validate>")
                return not tree.has_errors
            ast_root = convert_python_native_ast(content, "<validate>")
            return ast_root is not None
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Core parse method
    # ------------------------------------------------------------------

    def parse(
        self,
        job: AnalysisJob,
        context: ExecutionContext,
        options: Optional[ParserOptions] = None,
    ) -> ParserResult:
        """
        Parse a Python source file and return a fully populated ``ParserResult``.

        Steps
        -----
        1. Guard: plugin must be initialized.
        2. Read & decode source bytes (UTF-8 with latin-1 fallback).
        3. Guard: file size within limit.
        4. Delegate to ``TreeSitterEngine.parse()`` → ``ParseTree``.
        5. Convert ``ParseTree`` → DevBrain ``ASTRoot`` via ``PythonASTConverter``.
        6. Collect diagnostics from ERROR nodes in parse tree.
        7. Assemble ``ParserResult``.
        8. Validate via ``ParserValidator``; append validation warnings.
        9. Return ``ParserResult``.

        Error isolation: every exception is caught; a ``INTERNAL_ERROR``
        ``ParserResult`` is returned instead of propagating the exception.
        """
        if not self._is_initialized or self._engine is None:
            return self._error_result(
                job=job,
                status=ParserStatus.INTERNAL_ERROR,
                message="PythonParserPlugin is not initialized. Call initialize() first.",
            )

        opts = options or ParserOptions()
        wall_start = time.perf_counter()

        # ------------------------------------------------------------------
        # 1. Read source bytes
        # ------------------------------------------------------------------
        source_bytes, encoding, encoding_warning = self._read_source(job, opts)
        if source_bytes is None:
            return self._error_result(
                job=job,
                status=ParserStatus.ENCODING_ERROR,
                message=f"Cannot read source for '{job.file.path}': {encoding_warning}",
            )

        # ------------------------------------------------------------------
        # 2. File size check
        # ------------------------------------------------------------------
        max_bytes = opts.max_file_size_kb * 1024
        if len(source_bytes) > max_bytes:
            return self._error_result(
                job=job,
                status=ParserStatus.SKIPPED,
                message=(
                    f"File '{job.file.path}' exceeds max_file_size_kb limit "
                    f"({len(source_bytes)} > {max_bytes} bytes)."
                ),
            )

        # ------------------------------------------------------------------
        # 3. Parse with TreeSitterEngine or fallback to Native Python AST
        # ------------------------------------------------------------------
        ast_root: Optional[ASTRoot] = None
        converter_errors: List[ModelParserError] = []
        parse_tree: Optional[ParseTree] = None
        ast_node_count = 0

        source_str = source_bytes.decode(encoding, errors="replace")

        if self._engine and self._engine.is_language_loaded(_GRAMMAR_KEY):
            try:
                parse_tree = self._engine.parse(
                    _GRAMMAR_KEY,
                    source_bytes,
                    job.file.path,
                )
                converter = PythonASTConverter(max_depth=getattr(self, "_max_ast_depth", 200))
                ast_root = converter.convert(parse_tree, source_bytes)
                ast_node_count = converter.node_count
            except Exception as exc:
                logger.warning(f"[PythonParserPlugin] TreeSitter parse failed for '{job.file.path}': {exc}. Using native AST fallback.")
                parse_tree = None

        if ast_root is None:
            ast_root = convert_python_native_ast(source_str, job.file.path)
            ast_node_count = ast_root.total_nodes

        # ------------------------------------------------------------------
        # 5. Diagnostic collection from parse tree
        # ------------------------------------------------------------------
        if parse_tree is not None:
            parse_errors, parse_warnings = self._collect_diagnostics(
                parse_tree, source_bytes, opts
            )
        else:
            parse_errors, parse_warnings = [], []
        all_errors = parse_errors + converter_errors
        all_warnings: List[ModelParserWarning] = list(parse_warnings)

        # Encoding warning
        if encoding_warning:
            all_warnings.append(
                ModelParserWarning(
                    message=encoding_warning,
                    code="W001",
                )
            )

        # ------------------------------------------------------------------
        # 6. Determine status
        # ------------------------------------------------------------------
        if parse_tree and parse_tree.has_errors and all_errors:
            status = ParserStatus.PARTIAL_SUCCESS if ast_root else ParserStatus.SYNTAX_ERROR
        elif converter_errors:
            status = ParserStatus.PARTIAL_SUCCESS if ast_root else ParserStatus.INTERNAL_ERROR
        else:
            status = ParserStatus.SUCCESS

        # ------------------------------------------------------------------
        # 7. Metrics
        # ------------------------------------------------------------------
        wall_ms = (time.perf_counter() - wall_start) * 1000.0
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        lines_parsed = source_bytes.count(b"\n") + (1 if source_bytes else 0)
        memory_bytes = self._get_memory_bytes()

        statistics = ParserStatistics(
            duration_ms=round(wall_ms, 3),
            bytes_parsed=len(source_bytes),
            lines_parsed=lines_parsed,
            node_count=ast_node_count,
            error_count=len(all_errors),
            warning_count=len(all_warnings),
            memory_rss_bytes=memory_bytes,
        )

        metadata = ParserMetadata(
            parser_name=_PLUGIN_NAME,
            language=ParserLanguage.PYTHON,
            version=self.version,
            capabilities=self.capabilities,
            file_hash=source_hash,
        )

        # ------------------------------------------------------------------
        # 4.5 Extract raw symbols and raw imports
        # ------------------------------------------------------------------
        raw_symbols = []
        raw_imports = []
        if ast_root is not None:
            try:
                res = self._semantic_extractor.extract(ast_root)
                mod = res.module
                if mod:
                    for fn in mod.functions:
                        # Determine if this is an API route
                        kind = "api_route" if (fn.http_method and fn.route_path) else "function"
                        raw_symbols.append({
                            "kind": kind,
                            "name": fn.name,
                            "file_path": job.file.path,
                            "range": fn.range.model_dump() if fn.range else None,
                            "docstring": fn.docstring,
                            "signature": fn.name,
                            "http_method": fn.http_method,
                            "route_path": fn.route_path,
                        })
                    for cls in mod.classes:
                        raw_symbols.append({
                            "kind": "class",
                            "name": cls.name,
                            "file_path": job.file.path,
                            "range": cls.range.model_dump() if cls.range else None,
                            "docstring": cls.docstring,
                            "signature": cls.name,
                        })
                        for m in cls.methods:
                            # Determine if this is an API route
                            kind = "api_route" if (m.http_method and m.route_path) else "method"
                            raw_symbols.append({
                                "kind": kind,
                                "name": m.name,
                                "file_path": job.file.path,
                                "range": m.range.model_dump() if m.range else None,
                                "docstring": m.docstring,
                                "signature": f"{cls.name}.{m.name}",
                                "http_method": m.http_method,
                                "route_path": m.route_path,
                            })
                    for imp in mod.imports:
                        raw_imports.append({
                            "module": imp.module,
                            "imported_names": imp.imported_names,
                            "aliases": imp.aliases,
                            "file_path": job.file.path,
                            "range": imp.range.model_dump() if imp.range else None,
                        })
            except Exception as exc:
                logger.warning(f"[PythonParserPlugin] Semantic extraction failed for '{job.file.path}': {exc}")

        # ------------------------------------------------------------------
        # 8. Assemble ParserResult
        # ------------------------------------------------------------------
        result = ParserResult(
            job_id=job.job_id,
            file_path=job.file.path,
            language=ParserLanguage.PYTHON,
            status=status,
            errors=all_errors,
            warnings=all_warnings,
            statistics=statistics,
            metadata=metadata,
            ast_root=ast_root.model_dump() if ast_root else None,
            raw_symbols=raw_symbols,
            raw_imports=raw_imports,
        )

        # ------------------------------------------------------------------
        # 9. Automatic validation
        # ------------------------------------------------------------------
        try:
            validation_report = self._validator.validate_result(result)
            if not validation_report.is_valid:
                for err in validation_report.errors:
                    result.warnings.append(
                        ModelParserWarning(
                            message=f"[validation] {err.message}",
                            code=err.code.value if hasattr(err.code, "value") else str(err.code),
                        )
                    )
        except Exception as exc:
            logger.warning(f"[PythonParserPlugin] Validation raised exception: {exc}")

        # ------------------------------------------------------------------
        # 10. Update accumulators
        # ------------------------------------------------------------------
        self._total_parses += 1
        self._total_parse_ms += wall_ms
        self._total_ast_nodes += ast_node_count

        logger.debug(
            f"[PythonParserPlugin] Parsed '{job.file.path}' in {wall_ms:.2f}ms "
            f"(status={status.value}, nodes={ast_node_count}, errors={len(all_errors)})"
        )
        return result

    def extract_semantics(self, result: ParserResult) -> "SemanticExtractionResult":
        """
        Extract structured semantic entities from a `ParserResult` produced by `parse()`.

        Returns a `SemanticExtractionResult` containing ExtractedModule, ExtractedClass,
        ExtractedFunction, ExtractedVariable, ExtractedImport, etc.
        """
        from plugins.python.semantic_extractor import PythonSemanticExtractor
        extractor = PythonSemanticExtractor()
        return extractor.extract_result(result)

    # ------------------------------------------------------------------
    # Diagnostics collection
    # ------------------------------------------------------------------

    def _collect_diagnostics(
        self,
        parse_tree: ParseTree,
        source_bytes: bytes,
        opts: ParserOptions,
    ) -> Tuple[List[ModelParserError], List[ModelParserWarning]]:
        """
        Walk the parse tree wrapper and collect ERROR / MISSING nodes as
        ``ParserError`` records.  Also generates warnings for large files
        or suspiciously deep trees.
        """
        errors: List[ModelParserError] = []
        warnings: List[ModelParserWarning] = []

        # Collect ERROR nodes from the wrapped parse tree
        self._walk_errors(parse_tree.root_node, source_bytes, errors)

        # File size warning
        size_kb = len(source_bytes) / 1024.0
        if size_kb > opts.max_file_size_kb * 0.8:
            warnings.append(
                ModelParserWarning(
                    message=f"File size {size_kb:.1f} KB is near the {opts.max_file_size_kb} KB limit.",
                    code="W002",
                )
            )

        return errors, warnings

    def _walk_errors(
        self,
        node: "ParseTreeNode",  # type: ignore[name-defined]
        source_bytes: bytes,
        errors: List[ModelParserError],
        max_errors: int = 50,
    ) -> None:
        """Recursively collect ERROR/MISSING nodes into ``errors`` list."""
        if len(errors) >= max_errors:
            return

        if node.is_error or node.is_missing:
            row, col = node.start_point
            snippet: Optional[str] = None
            try:
                snippet = source_bytes[node.start_byte:min(node.end_byte, node.start_byte + 80)].decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                pass

            errors.append(
                ModelParserError(
                    message=(
                        f"{'MISSING' if node.is_missing else 'Syntax error'} at "
                        f"line {row + 1}, col {col}: [{node.node_type}]"
                        + (f": {snippet!r}" if snippet else "")
                    ),
                    line=max(1, row + 1),
                    column=col,
                    start_byte=node.start_byte,
                    end_byte=node.end_byte,
                    severity="error",
                    node_type=node.node_type,
                    snippet=snippet,
                )
            )

        for child in node.children:
            self._walk_errors(child, source_bytes, errors, max_errors)

    # ------------------------------------------------------------------
    # Source reading
    # ------------------------------------------------------------------

    def _read_source(
        self,
        job: AnalysisJob,
        opts: ParserOptions,
    ) -> Tuple[Optional[bytes], str, Optional[str]]:
        """
        Read and return the source bytes for ``job.file``.

        Returns ``(bytes, encoding, warning_or_None)``.

        Strategy:
        1. Check for ``_content_bytes`` (private test-injection bytes attribute).
        2. If ``job.file.content`` is a non-empty str (RepositoryFile model), encode it.
        3. Otherwise, read from ``job.file.absolute_path`` or ``path`` on disk.
        4. Attempt UTF-8 decode; if that fails, fall back to latin-1 and emit a warning.
        """
        file_ref = job.file

        # Strategy A: private bytes attribute injected in tests
        content_bytes = getattr(file_ref, "_content_bytes", None)
        if isinstance(content_bytes, bytes):
            try:
                content_bytes.decode("utf-8")
                return content_bytes, "utf-8", None
            except UnicodeDecodeError:
                return content_bytes, "latin-1", (
                    f"File '{job.file.path}' is not valid UTF-8; parsed with latin-1 fallback. "
                    "Symbol names may be incorrect."
                )

        # Strategy B: RepositoryFile.content is Optional[str]
        content_str = getattr(file_ref, "content", None)
        if isinstance(content_str, str):
            raw = content_str.encode("utf-8", errors="replace")
            return raw, "utf-8", None

        # Strategy C: read from disk
        file_path = getattr(file_ref, "absolute_path", None) or getattr(file_ref, "path", None)
        if not file_path or not os.path.exists(str(file_path)):
            return None, "unknown", f"File not found: {file_path}"

        try:
            with open(str(file_path), "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            return None, "unknown", f"Cannot read file: {exc}"

        # Attempt UTF-8 decode to check encoding
        try:
            raw.decode("utf-8")
            return raw, "utf-8", None
        except UnicodeDecodeError:
            # Fall back to latin-1 — always succeeds (byte-transparent)
            return raw, "latin-1", (
                f"File '{file_path}' is not valid UTF-8; parsed with latin-1 fallback. "
                "Symbol names may be incorrect."
            )

    # ------------------------------------------------------------------
    # Error result factory
    # ------------------------------------------------------------------

    def _error_result(
        self,
        job: AnalysisJob,
        status: ParserStatus,
        message: str,
        line: int = 1,
    ) -> ParserResult:
        """Build a minimal ``ParserResult`` for a failure path."""
        return ParserResult(
            job_id=job.job_id,
            file_path=job.file.path,
            language=ParserLanguage.PYTHON,
            status=status,
            errors=[ModelParserError(message=message, line=line, severity="error")],
            metadata=ParserMetadata(
                parser_name=_PLUGIN_NAME,
                language=ParserLanguage.PYTHON,
                version=self.version,
                capabilities=self.capabilities,
            ),
        )

    # ------------------------------------------------------------------
    # Resource utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _get_memory_bytes() -> int:
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            return proc.memory_info().rss
        except Exception:
            return 0
