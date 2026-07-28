"""
core/tree_sitter_engine/tree_sitter_engine.py
----------------------------------------------
Phase 4.1 — Tree-sitter Engine (Top-Level Coordinator).

``TreeSitterEngine`` is the single public surface of the tree-sitter
backend.  It owns ``GrammarLoader``, ``LanguageCache``, and ``ParserCache``,
and provides a clean API for:

- Initialising grammars (``initialize``)
- Parsing source bytes into a ``ParseTree`` wrapper (``parse``)
- Health reporting (``health_check``)
- Graceful shutdown (``shutdown``)

Tree-sitter Object Containment
-------------------------------
The fundamental contract of this module:

  **No** ``tree_sitter.Language``, ``tree_sitter.Parser``, ``tree_sitter.Tree``,
  or ``tree_sitter.Node`` objects EVER leave this file.

All such objects are translated into ``ParseTreeNode`` / ``ParseTree``
value objects (defined in ``models.tree_sitter_models``) before returning.
This isolation ensures:

1. Callers are never accidentally pinned to a specific tree-sitter version.
2. Serialization / deep-copying is always safe.
3. Testing can be done without a live tree-sitter installation if needed.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, List, Optional

try:
    from tree_sitter import Node as TSNode, Tree as TSTree
except ImportError:
    class TSNode: pass  # type: ignore
    class TSTree: pass  # type: ignore


from core.tree_sitter_engine.grammar_loader import GrammarLoader, LANGUAGE_KEYS
from core.tree_sitter_engine.language_cache import LanguageCache
from core.tree_sitter_engine.parser_cache import ParserCache
from models.health import ComponentHealth, HealthStatus
from models.parser import ParserLanguage
from models.tree_sitter_models import (
    EngineMetrics,
    GrammarVersion,
    ParseTree,
    ParseTreeNode,
    ParserHealth,
)
from utils.exceptions import ErrorCode, ParserError
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import psutil as _psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def _convert_node(ts_node: TSNode, source_bytes: bytes, max_depth: int = 50, _depth: int = 0) -> ParseTreeNode:
    """
    Recursively convert a ``tree_sitter.Node`` into a ``ParseTreeNode``.

    Leaf nodes (no children) receive their ``text`` field populated from
    ``source_bytes``.  Named-only children are included; anonymous tokens
    are included too so callers have a complete faithful tree.

    Parameters
    ----------
    ts_node:
        Native tree-sitter Node.
    source_bytes:
        Original source bytes — used to extract leaf text.
    max_depth:
        Maximum recursion depth to prevent stack overflow on pathological trees.
    _depth:
        Current recursion depth (internal).
    """
    text: Optional[str] = None
    children: List[ParseTreeNode] = []

    if _depth < max_depth:
        for child in ts_node.children:
            children.append(_convert_node(child, source_bytes, max_depth, _depth + 1))
    elif ts_node.children:
        # Signal truncation at max_depth
        children = [
            ParseTreeNode(
                node_type="__depth_limit__",
                is_named=False,
                is_error=False,
                is_missing=False,
                start_byte=ts_node.start_byte,
                end_byte=ts_node.end_byte,
                start_point=ts_node.start_point,
                end_point=ts_node.end_point,
            )
        ]

    if not ts_node.children:
        # Leaf node — extract text safely
        try:
            text = source_bytes[ts_node.start_byte:ts_node.end_byte].decode("utf-8", errors="replace")
        except Exception:
            text = None

    return ParseTreeNode(
        node_type=ts_node.type,
        is_named=ts_node.is_named,
        is_error=ts_node.is_error,
        is_missing=ts_node.is_missing,
        start_byte=ts_node.start_byte,
        end_byte=ts_node.end_byte,
        start_point=ts_node.start_point,
        end_point=ts_node.end_point,
        text=text,
        child_count=ts_node.child_count,
        children=children,
    )


def _count_errors(ts_node: TSNode) -> int:
    """Count ERROR and MISSING nodes in the parse tree."""
    count = 1 if (ts_node.is_error or ts_node.is_missing) else 0
    for child in ts_node.children:
        count += _count_errors(child)
    return count


class TreeSitterEngine:
    """
    Thread-safe Tree-sitter parsing backend.

    Maintains one ``Language`` object and one ``Parser`` instance per grammar key.
    Native tree-sitter objects do not escape the ``parse()`` boundary.

    Typical lifecycle::

        engine = TreeSitterEngine()
        engine.initialize([ParserLanguage.PYTHON, ParserLanguage.TYPESCRIPT])

        tree: ParseTree = engine.parse("python", b"def hello(): pass", "hello.py")
        health: ParserHealth = engine.health_check()
        engine.shutdown()
    """

    def __init__(self) -> None:
        self._grammar_loader = GrammarLoader()
        self._language_cache = LanguageCache()
        self._parser_cache = ParserCache()

        self._is_initialized: bool = False
        self._init_lock: threading.Lock = threading.Lock()
        self._start_time: Optional[float] = None

        # Benchmark / metrics counters (guarded by _metrics_lock)
        self._metrics_lock: threading.Lock = threading.Lock()
        self._metrics = EngineMetrics()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(
        self,
        languages: Optional[List[ParserLanguage]] = None,
    ) -> List[GrammarVersion]:
        """
        Load grammars and pre-create parsers for all requested languages.

        Parameters
        ----------
        languages:
            Languages to load.  If ``None``, all supported languages are loaded.

        Returns
        -------
        List[GrammarVersion]
            One record per grammar key attempted, including failures.
        """
        with self._init_lock:
            if self._is_initialized:
                logger.warning("[TreeSitterEngine] Already initialized — skipping.")
                return self._language_cache.list_all_versions()

            target_languages = languages or list(LANGUAGE_KEYS.keys())
            results: List[GrammarVersion] = []

            for parser_language in target_languages:
                keys = LANGUAGE_KEYS.get(parser_language, [])
                for key in keys:
                    gv = self._load_grammar(key)
                    results.append(gv)

            self._is_initialized = True
            self._start_time = time.monotonic()

            loaded = sum(1 for r in results if r.is_loaded)
            logger.info(
                f"[TreeSitterEngine] Initialized — {loaded}/{len(results)} grammars loaded: "
                f"{[r.language_key for r in results if r.is_loaded]}"
            )
            return results

    def _load_grammar(self, language_key: str) -> GrammarVersion:
        """Load a single grammar by key and register its Parser.  Internal."""
        if self._language_cache.is_loaded(language_key):
            gv = self._language_cache.get_version(language_key)
            logger.debug(f"[TreeSitterEngine] Grammar '{language_key}' already in cache.")
            return gv

        load_start = time.perf_counter()
        native_lang, gv = self._grammar_loader.load_safe(language_key)
        load_ms = (time.perf_counter() - load_start) * 1000.0

        if native_lang is not None:
            self._language_cache.store(language_key, native_lang, gv, load_ms)
            self._parser_cache.register(language_key, native_lang)

            with self._metrics_lock:
                self._metrics.grammar_load_times_ms[language_key] = round(load_ms, 3)
                self._metrics.parser_creation_count[language_key] = 1
        else:
            self._language_cache.store_error(language_key, gv)

        return gv

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse(
        self,
        language_key: str,
        source: bytes,
        file_path: str = "<unknown>",
    ) -> ParseTree:
        """
        Parse ``source`` bytes with the grammar for ``language_key``.

        Parameters
        ----------
        language_key:
            Grammar key, e.g. ``"python"``, ``"typescript"``, ``"tsx"``.
        source:
            UTF-8 encoded source bytes.
        file_path:
            Informational file path embedded in the returned ``ParseTree``.

        Returns
        -------
        ParseTree
            Wrapped parse result.  No native tree-sitter objects inside.

        Raises
        ------
        ParserError
            If the engine is not initialized, grammar is not loaded,
            or an unexpected parsing failure occurs.
        """
        if not self._is_initialized:
            raise ParserError(
                "[TreeSitterEngine] Engine not initialized. Call initialize() first.",
                code=ErrorCode.PARSER_UNSUPPORTED,
            )

        if not self._parser_cache.is_registered(language_key):
            raise ParserError(
                f"[TreeSitterEngine] No parser registered for language key '{language_key}'. "
                f"Available: {self._parser_cache.registered_keys()}",
                code=ErrorCode.PARSER_UNSUPPORTED,
            )

        parse_start = time.perf_counter()

        try:
            with self._parser_cache.borrow(language_key) as parser:
                ts_tree: TSTree = parser.parse(source)
        except KeyError as exc:
            raise ParserError(str(exc), code=ErrorCode.PARSER_UNSUPPORTED) from exc
        except Exception as exc:
            with self._metrics_lock:
                self._metrics.error_count += 1
            raise ParserError(
                f"[TreeSitterEngine] Unexpected parse failure for '{language_key}': {exc}",
                code=ErrorCode.PARSER_SYNTAX_ERROR,
            ) from exc

        parse_ms = (time.perf_counter() - parse_start) * 1000.0

        # Translate native tree into our wrapper — no native objects escape
        root_wrapper = _convert_node(ts_tree.root_node, source)
        error_count = _count_errors(ts_tree.root_node)

        parse_tree = ParseTree(
            file_path=file_path,
            language_key=language_key,
            root_node=root_wrapper,
            source_bytes=len(source),
            error_node_count=error_count,
            has_errors=ts_tree.root_node.has_error,
            parse_duration_ms=round(parse_ms, 3),
        )

        # Update benchmarks
        with self._metrics_lock:
            self._metrics.total_parses += 1
            self._metrics.total_parse_ms += parse_ms
            reuse = self._parser_cache.reuse_counts()
            self._metrics.parser_reuse_count = reuse

        logger.debug(
            f"[TreeSitterEngine] Parsed '{file_path}' ({language_key}) "
            f"in {parse_ms:.2f}ms, errors={error_count}"
        )
        return parse_tree

    # ------------------------------------------------------------------
    # Health & Metrics
    # ------------------------------------------------------------------

    def health_check(self) -> ParserHealth:
        """
        Return a ``ParserHealth`` snapshot describing the engine state.

        All fields are plain Python data — no tree-sitter objects.
        """
        uptime = (time.monotonic() - self._start_time) if self._start_time else 0.0
        memory_mb = self._get_memory_mb()

        grammar_versions = self._language_cache.list_all_versions()
        loaded_count = sum(1 for g in grammar_versions if g.is_loaded)
        errors = [g.load_error for g in grammar_versions if g.load_error]

        return ParserHealth(
            is_running=self._is_initialized,
            grammar_count=loaded_count,
            cached_parser_count=self._parser_cache.size,
            grammars=grammar_versions,
            errors=errors,
            uptime_seconds=round(uptime, 2),
            memory_rss_mb=memory_mb,
        )

    def component_health(self) -> ComponentHealth:
        """Return a ``ComponentHealth`` record for integration with ``ParserManager.health_check()``."""
        ph = self.health_check()
        status = HealthStatus.HEALTHY if (ph.is_running and ph.grammar_count > 0) else HealthStatus.DEGRADED
        if not ph.is_running:
            status = HealthStatus.UNHEALTHY

        return ComponentHealth(
            name="TreeSitterEngine",
            status=status,
            message=(
                f"Running: {ph.is_running}, Grammars: {ph.grammar_count}, "
                f"Parsers: {ph.cached_parser_count}, Uptime: {ph.uptime_seconds:.0f}s"
            ),
            errors=ph.errors,
            details={
                "grammar_count": ph.grammar_count,
                "cached_parsers": ph.cached_parser_count,
                "grammars": {g.language_key: g.is_loaded for g in ph.grammars},
                "uptime_seconds": ph.uptime_seconds,
                "memory_rss_mb": ph.memory_rss_mb,
            },
        )

    def get_metrics(self) -> EngineMetrics:
        """Return current engine metrics snapshot."""
        with self._metrics_lock:
            return self._metrics.model_copy()

    def get_grammar_version(self, language_key: str) -> Optional[GrammarVersion]:
        """Return ``GrammarVersion`` metadata for ``language_key``."""
        return self._language_cache.get_version(language_key)

    def is_language_loaded(self, language_key: str) -> bool:
        """Return True if the grammar for ``language_key`` is loaded and ready."""
        return self._language_cache.is_loaded(language_key)

    def loaded_language_keys(self) -> List[str]:
        """Return all language keys whose grammars loaded successfully."""
        return self._language_cache.list_loaded_keys()

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Release all cached parsers and language objects."""
        with self._init_lock:
            if not self._is_initialized:
                return
            self._parser_cache.clear()
            self._language_cache.clear()
            self._is_initialized = False
            self._start_time = None
            logger.info("[TreeSitterEngine] Shutdown complete — all resources released.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_memory_mb() -> float:
        if _HAS_PSUTIL:
            try:
                import psutil
                proc = psutil.Process(os.getpid())
                return round(proc.memory_info().rss / (1024 * 1024), 2)
            except Exception:
                pass
        return 0.0
