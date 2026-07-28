"""
core/tree_sitter_engine/language_cache.py
------------------------------------------
Phase 4.1 — Tree-sitter Language Cache.

Thread-safe cache storing ``tree_sitter.Language`` objects keyed by
language key (e.g. ``"python"``, ``"typescript"``).

Architecture Decision
---------------------
``Language`` objects are immutable grammar descriptors — one per grammar,
shared across all ``Parser`` instances for that language.
Separating the language cache from the parser cache makes this sharing explicit
and avoids duplicating grammar memory across threads.

Thread Safety
-------------
A single ``threading.RLock`` guards all mutation operations.  Read-only lookups
after initial population are lock-free since Python dict reads are GIL-safe,
but we still hold the lock for consistency.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from tree_sitter import Language
except ImportError:
    class Language:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError("tree_sitter C-binding unavailable")


from models.tree_sitter_models import GrammarVersion
from utils.logger import get_logger

logger = get_logger(__name__)


class LanguageCache:
    """
    Thread-safe store of loaded ``tree_sitter.Language`` objects.

    ``Language`` instances are created once by ``GrammarLoader`` and then
    stored here for the lifetime of the engine.  They are *never* returned
    to external callers — only ``TreeSitterEngine`` accesses this cache
    internally.
    """

    def __init__(self) -> None:
        self._lock: threading.RLock = threading.RLock()
        # language_key → Language
        self._languages: Dict[str, Language] = {}
        # language_key → GrammarVersion metadata
        self._grammar_versions: Dict[str, GrammarVersion] = {}
        # language_key → load time in ms (for benchmarks)
        self._load_times_ms: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Insertion
    # ------------------------------------------------------------------

    def store(
        self,
        language_key: str,
        language: Language,
        grammar_version: GrammarVersion,
        load_duration_ms: float = 0.0,
    ) -> None:
        """
        Store a loaded ``Language`` and its version metadata.

        Parameters
        ----------
        language_key:
            Canonical grammar key (e.g. ``"python"``).
        language:
            The ``tree_sitter.Language`` object to cache.
        grammar_version:
            Associated ``GrammarVersion`` metadata record.
        load_duration_ms:
            How long the grammar took to load (benchmarking).
        """
        with self._lock:
            self._languages[language_key] = language
            self._grammar_versions[language_key] = grammar_version.model_copy(
                update={
                    "is_loaded": True,
                    "loaded_at": datetime.now(timezone.utc),
                }
            )
            self._load_times_ms[language_key] = load_duration_ms
            logger.debug(
                f"[LanguageCache] Stored '{language_key}' "
                f"(abi={grammar_version.abi_version}, load={load_duration_ms:.2f}ms)"
            )

    def store_error(self, language_key: str, grammar_version: GrammarVersion) -> None:
        """Record a failed grammar load without storing a Language."""
        with self._lock:
            self._grammar_versions[language_key] = grammar_version
            logger.debug(
                f"[LanguageCache] Stored error entry for '{language_key}': {grammar_version.load_error}"
            )

    # ------------------------------------------------------------------
    # Retrieval (internal only — callers must not expose Language objects)
    # ------------------------------------------------------------------

    def get(self, language_key: str) -> Optional[Language]:
        """Return cached ``Language`` or ``None`` if not loaded."""
        with self._lock:
            return self._languages.get(language_key)

    def is_loaded(self, language_key: str) -> bool:
        """Return True if the grammar for ``language_key`` is successfully cached."""
        with self._lock:
            return language_key in self._languages

    def get_version(self, language_key: str) -> Optional[GrammarVersion]:
        """Return ``GrammarVersion`` metadata for ``language_key``."""
        with self._lock:
            return self._grammar_versions.get(language_key)

    def list_loaded_keys(self) -> List[str]:
        """Return all keys whose Language loaded successfully."""
        with self._lock:
            return [k for k, v in self._grammar_versions.items() if v.is_loaded]

    def list_all_versions(self) -> List[GrammarVersion]:
        """Return all GrammarVersion records (loaded and failed)."""
        with self._lock:
            return list(self._grammar_versions.values())

    def load_times(self) -> Dict[str, float]:
        """Return grammar-key → load-time-ms map (benchmark data)."""
        with self._lock:
            return dict(self._load_times_ms)

    @property
    def size(self) -> int:
        """Number of successfully loaded grammars."""
        with self._lock:
            return len(self._languages)

    def clear(self) -> None:
        """Remove all cached entries (called during engine shutdown)."""
        with self._lock:
            self._languages.clear()
            self._grammar_versions.clear()
            self._load_times_ms.clear()
            logger.debug("[LanguageCache] Cleared all grammar entries")
