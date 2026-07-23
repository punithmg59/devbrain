"""
core/tree_sitter_engine/parser_cache.py
----------------------------------------
Phase 4.1 — Tree-sitter Parser Cache.

Manages a pool of ``tree_sitter.Parser`` instances — one per language key.

Architecture Decision: Per-Language Single Parser with Locking
--------------------------------------------------------------
The Tree-sitter ``Parser`` object is NOT thread-safe; it cannot be shared
across simultaneous parse calls for the same language.  We use a
per-language ``threading.Lock`` so:

1. Different languages parse concurrently (full parallelism across languages).
2. Same-language parses are serialized (correctness guarantee).

This is far more efficient than a naïve global lock and avoids the complexity
of a full parser pool (queue of N parsers per language), which adds overhead
without measurable benefit for typical repository analysis workloads where
concurrent same-language parses are rare.

Future: If profiling shows same-language contention, ``ParserCache`` can
be evolved into a per-language ``queue.Queue`` of parser instances without
changing the public interface.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Dict, Generator, Optional

from tree_sitter import Language, Parser

from utils.logger import get_logger

logger = get_logger(__name__)


class ParserCache:
    """
    Thread-safe cache of ``tree_sitter.Parser`` instances, keyed by language key.

    Provides a context-manager interface (``borrow()``) for safe, locked
    access to a Parser for a specific language.
    """

    def __init__(self) -> None:
        # language_key → Parser (created lazily on first use)
        self._parsers: Dict[str, Parser] = {}
        # language_key → RLock (per-language serialization)
        self._parser_locks: Dict[str, threading.Lock] = {}
        # Guards _parsers and _parser_locks dictionaries themselves
        self._registry_lock: threading.Lock = threading.Lock()

        # Benchmark counters
        self._reuse_count: Dict[str, int] = {}
        self._creation_count: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Registration (called once per language during engine init)
    # ------------------------------------------------------------------

    def register(self, language_key: str, language: Language) -> None:
        """
        Pre-create and register a ``Parser`` for ``language_key``.

        Parameters
        ----------
        language_key:
            Canonical grammar key, e.g. ``"python"``.
        language:
            The ``tree_sitter.Language`` to bind to the parser.
        """
        with self._registry_lock:
            if language_key in self._parsers:
                logger.debug(
                    f"[ParserCache] Parser for '{language_key}' already registered — skipping."
                )
                return

            parser = Parser(language)
            self._parsers[language_key] = parser
            self._parser_locks[language_key] = threading.Lock()
            self._reuse_count[language_key] = 0
            self._creation_count[language_key] = 1

            logger.debug(f"[ParserCache] Registered parser for '{language_key}'")

    # ------------------------------------------------------------------
    # Borrowing (thread-safe parse window)
    # ------------------------------------------------------------------

    @contextmanager
    def borrow(self, language_key: str) -> Generator[Parser, None, None]:
        """
        Context manager that yields a ``Parser`` locked to the current thread.

        Usage::

            with parser_cache.borrow("python") as parser:
                tree = parser.parse(source_bytes)

        Raises
        ------
        KeyError
            If ``language_key`` is not registered.
        """
        with self._registry_lock:
            parser = self._parsers.get(language_key)
            lock = self._parser_locks.get(language_key)

        if parser is None or lock is None:
            raise KeyError(
                f"[ParserCache] No parser registered for '{language_key}'. "
                f"Available: {list(self._parsers)}"
            )

        start_wait = time.perf_counter()
        with lock:
            wait_ms = (time.perf_counter() - start_wait) * 1000.0
            if wait_ms > 50:
                logger.warning(
                    f"[ParserCache] Thread waited {wait_ms:.1f}ms for '{language_key}' parser lock."
                )

            with self._registry_lock:
                self._reuse_count[language_key] = self._reuse_count.get(language_key, 0) + 1

            yield parser

    # ------------------------------------------------------------------
    # Queries (benchmark data)
    # ------------------------------------------------------------------

    def is_registered(self, language_key: str) -> bool:
        """Return True if a Parser for ``language_key`` has been registered."""
        with self._registry_lock:
            return language_key in self._parsers

    def registered_keys(self) -> list[str]:
        """Return all registered language keys."""
        with self._registry_lock:
            return list(self._parsers.keys())

    def reuse_counts(self) -> Dict[str, int]:
        """Return dict of language_key → cumulative borrow count."""
        with self._registry_lock:
            return dict(self._reuse_count)

    def creation_counts(self) -> Dict[str, int]:
        """Return dict of language_key → Parser creation count."""
        with self._registry_lock:
            return dict(self._creation_count)

    @property
    def size(self) -> int:
        """Number of cached Parser instances."""
        with self._registry_lock:
            return len(self._parsers)

    def clear(self) -> None:
        """Remove all cached parsers (called on engine shutdown)."""
        with self._registry_lock:
            self._parsers.clear()
            self._parser_locks.clear()
            self._reuse_count.clear()
            self._creation_count.clear()
            logger.debug("[ParserCache] Cleared all parser entries")
