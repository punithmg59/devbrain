"""
core/tree_sitter_engine/grammar_loader.py
------------------------------------------
Phase 4.1 — Tree-sitter Grammar Loader.

Responsible for importing Python grammar bindings and creating
``tree_sitter.Language`` objects. Grammars are loaded once and shared
via the ``LanguageCache`` — this module contains only the loading logic.

Architecture Decision
---------------------
Separating loading from caching follows the Single Responsibility Principle:
``GrammarLoader`` knows *how* to load a grammar; ``LanguageCache`` knows *where*
to store it. This makes both independently testable and replaceable.
"""

from __future__ import annotations

import importlib
import time
from typing import Any, Callable, Dict, Optional

try:
    from tree_sitter import Language
except ImportError:
    class Language:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError("tree_sitter C-binding unavailable")


from models.parser import ParserLanguage
from models.tree_sitter_models import GrammarVersion
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Language Key Mappings
# ---------------------------------------------------------------------------

#: Map ParserLanguage → (grammar_module, factory_callable_name, package_display_name)
#: TypeScript requires two grammars (plain TS + TSX variant).
_GRAMMAR_SPECS: Dict[str, tuple[str, str, str]] = {
    "python":     ("tree_sitter_python",    "language",           "tree-sitter-python"),
    "javascript": ("tree_sitter_javascript", "language",          "tree-sitter-javascript"),
    "java":       ("tree_sitter_java",       "language",          "tree-sitter-java"),
    "go":         ("tree_sitter_go",         "language",          "tree-sitter-go"),
    "csharp":     ("tree_sitter_c_sharp",    "language",          "tree-sitter-c-sharp"),
    # TypeScript exposes two separate grammar entry-points
    "typescript": ("tree_sitter_typescript", "language_typescript", "tree-sitter-typescript"),
    "tsx":        ("tree_sitter_typescript", "language_tsx",       "tree-sitter-typescript"),
}

#: ParserLanguage → canonical language key(s) used in _GRAMMAR_SPECS
LANGUAGE_KEYS: Dict[ParserLanguage, list[str]] = {
    ParserLanguage.PYTHON:     ["python"],
    ParserLanguage.JAVASCRIPT: ["javascript"],
    ParserLanguage.TYPESCRIPT: ["typescript", "tsx"],
    ParserLanguage.JAVA:       ["java"],
    ParserLanguage.GO:         ["go"],
    ParserLanguage.CSHARP:     ["csharp"],
}


class GrammarLoader:
    """
    Loads Tree-sitter grammar bindings from installed Python packages.

    Each grammar key maps to a specific Python package exposing a callable that
    returns a raw grammar pointer accepted by ``tree_sitter.Language()``.

    All loaded ``Language`` objects are returned to callers; caching is handled
    by the ``LanguageCache`` that consumes this loader.
    """

    def load(self, language_key: str) -> tuple[Language, GrammarVersion]:
        """
        Load and return a ``tree_sitter.Language`` for ``language_key``.

        Parameters
        ----------
        language_key:
            One of the keys defined in ``_GRAMMAR_SPECS`` (e.g. ``"python"``,
            ``"typescript"``, ``"tsx"``).

        Returns
        -------
        (Language, GrammarVersion)
            Native Language object (not exposed beyond engine boundary) and
            its version metadata record.

        Raises
        ------
        ImportError
            If the backing Python package is not installed.
        AttributeError
            If the package does not expose the expected callable.
        RuntimeError
            If Language construction fails.
        """
        spec = _GRAMMAR_SPECS.get(language_key)
        if spec is None:
            raise ValueError(
                f"[GrammarLoader] No grammar spec registered for language key '{language_key}'. "
                f"Supported keys: {list(_GRAMMAR_SPECS)}"
            )

        module_name, factory_name, package_display = spec
        start_time = time.perf_counter()

        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            raise ImportError(
                f"[GrammarLoader] Grammar package '{module_name}' not installed. "
                f"Install it via: pip install {package_display}"
            ) from exc

        factory: Optional[Callable] = getattr(module, factory_name, None)
        if factory is None or not callable(factory):
            raise AttributeError(
                f"[GrammarLoader] Module '{module_name}' does not expose callable '{factory_name}'."
            )

        try:
            raw_lang = factory()
            language = Language(raw_lang)
        except Exception as exc:
            raise RuntimeError(
                f"[GrammarLoader] Failed to construct Language for '{language_key}': {exc}"
            ) from exc

        load_ms = (time.perf_counter() - start_time) * 1000.0
        abi = getattr(language, "abi_version", 0) or getattr(language, "version", 0)

        grammar_version = GrammarVersion(
            language_key=language_key,
            package_name=package_display,
            abi_version=int(abi),
            is_loaded=True,
            load_error=None,
        )

        logger.info(
            f"[GrammarLoader] Loaded '{language_key}' grammar in {load_ms:.2f}ms "
            f"(package={package_display}, abi={abi})"
        )
        return language, grammar_version

    def load_safe(self, language_key: str) -> tuple[Optional[Language], GrammarVersion]:
        """
        Attempt to load a grammar; returns ``(None, GrammarVersion(is_loaded=False))``
        on failure rather than raising.

        Safe variant used by ``TreeSitterEngine.initialize()`` so that partial
        grammar availability does not abort the entire engine startup.
        """
        try:
            lang, gv = self.load(language_key)
            return lang, gv
        except Exception as exc:
            err_msg = str(exc)
            logger.warning(f"[GrammarLoader] Failed to load '{language_key}': {err_msg}")
            return None, GrammarVersion(
                language_key=language_key,
                package_name=_GRAMMAR_SPECS.get(language_key, ("", "", ""))[2],
                abi_version=0,
                is_loaded=False,
                load_error=err_msg,
            )

    @staticmethod
    def supported_language_keys() -> list[str]:
        """Return all registered grammar keys."""
        return list(_GRAMMAR_SPECS.keys())

    @staticmethod
    def language_keys_for(parser_language: ParserLanguage) -> list[str]:
        """Return the grammar key(s) associated with a ``ParserLanguage`` enum value."""
        return LANGUAGE_KEYS.get(parser_language, [])
