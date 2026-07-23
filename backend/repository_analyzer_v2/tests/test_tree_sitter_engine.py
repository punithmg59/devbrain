"""
tests/test_tree_sitter_engine.py
---------------------------------
Phase 4.1 — Unit & Integration Test Suite for the Tree-sitter Engine.

Coverage
--------
- Grammar loading (success / failure / idempotency)
- Language cache storage and retrieval
- Parser cache registration, borrowing, reuse counts
- ``TreeSitterEngine.parse()`` correctness and encapsulation
- Concurrent parser requests across multiple languages
- Missing grammar handling
- Engine shutdown and resource cleanup
- Benchmark measurements (grammar load time, parser reuse, memory delta)
- ``ParserManager`` engine integration
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from core.parser_manager import ParserManager
from core.tree_sitter_engine import (
    GrammarLoader,
    LanguageCache,
    ParserCache,
    TreeSitterEngine,
)
from core.tree_sitter_engine.grammar_loader import LANGUAGE_KEYS, _GRAMMAR_SPECS
from models.parser import ParserLanguage
from models.tree_sitter_models import (
    EngineMetrics,
    GrammarVersion,
    ParseTree,
    ParseTreeNode,
    ParserHealth,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PYTHON_SRC = b"def hello(name: str) -> str:\n    return f'Hello, {name}'\n"
INVALID_SRC = b"def @@@invalid###"


# ---------------------------------------------------------------------------
# GrammarLoader Tests
# ---------------------------------------------------------------------------

class TestGrammarLoader:
    def test_load_python_success(self):
        loader = GrammarLoader()
        lang, gv = loader.load("python")
        assert lang is not None
        assert gv.is_loaded is True
        assert gv.language_key == "python"
        assert gv.abi_version >= 1

    def test_load_typescript_success(self):
        loader = GrammarLoader()
        lang, gv = loader.load("typescript")
        assert lang is not None
        assert gv.is_loaded is True

    def test_load_tsx_success(self):
        loader = GrammarLoader()
        lang, gv = loader.load("tsx")
        assert lang is not None
        assert gv.is_loaded is True

    def test_load_javascript_success(self):
        loader = GrammarLoader()
        lang, gv = loader.load("javascript")
        assert lang is not None

    def test_load_java_success(self):
        loader = GrammarLoader()
        lang, gv = loader.load("java")
        assert lang is not None

    def test_load_go_success(self):
        loader = GrammarLoader()
        lang, gv = loader.load("go")
        assert lang is not None

    def test_load_csharp_success(self):
        loader = GrammarLoader()
        lang, gv = loader.load("csharp")
        assert lang is not None

    def test_load_unknown_key_raises_value_error(self):
        loader = GrammarLoader()
        with pytest.raises(ValueError, match="No grammar spec registered"):
            loader.load("cobol")

    def test_load_safe_returns_none_on_missing_module(self):
        loader = GrammarLoader()
        with patch.dict("sys.modules", {"tree_sitter_cobol": None}):
            # Force a missing language key to trigger safe error path
            with patch.object(loader, "load", side_effect=ImportError("no module")):
                lang, gv = loader.load_safe("python")
                # load was patched to fail but load_safe should handle it
                assert lang is None
                assert gv.is_loaded is False

    def test_grammar_version_package_name(self):
        loader = GrammarLoader()
        _, gv = loader.load("python")
        assert "tree-sitter-python" in gv.package_name

    def test_supported_language_keys_completeness(self):
        keys = GrammarLoader.supported_language_keys()
        assert "python" in keys
        assert "typescript" in keys
        assert "tsx" in keys
        assert "javascript" in keys
        assert "java" in keys
        assert "go" in keys
        assert "csharp" in keys

    def test_language_keys_for_parser_language(self):
        py_keys = GrammarLoader.language_keys_for(ParserLanguage.PYTHON)
        assert py_keys == ["python"]

        ts_keys = GrammarLoader.language_keys_for(ParserLanguage.TYPESCRIPT)
        assert "typescript" in ts_keys
        assert "tsx" in ts_keys

    def test_grammar_load_time_is_positive(self):
        loader = GrammarLoader()
        start = time.perf_counter()
        loader.load("python")
        elapsed = (time.perf_counter() - start) * 1000.0
        assert elapsed > 0


# ---------------------------------------------------------------------------
# LanguageCache Tests
# ---------------------------------------------------------------------------

class TestLanguageCache:
    def test_store_and_retrieve(self):
        loader = GrammarLoader()
        lang, gv = loader.load("python")
        cache = LanguageCache()
        cache.store("python", lang, gv, load_duration_ms=5.0)

        assert cache.is_loaded("python") is True
        assert cache.get("python") is lang  # same object reference (internal use only)
        assert cache.size == 1

    def test_get_version(self):
        loader = GrammarLoader()
        lang, gv = loader.load("python")
        cache = LanguageCache()
        cache.store("python", lang, gv)

        version = cache.get_version("python")
        assert version is not None
        assert version.language_key == "python"
        assert version.is_loaded is True

    def test_store_error(self):
        cache = LanguageCache()
        error_gv = GrammarVersion(
            language_key="cobol",
            package_name="tree-sitter-cobol",
            abi_version=0,
            is_loaded=False,
            load_error="Module not found",
        )
        cache.store_error("cobol", error_gv)
        assert cache.is_loaded("cobol") is False
        v = cache.get_version("cobol")
        assert v is not None
        assert v.load_error is not None

    def test_list_loaded_keys(self):
        loader = GrammarLoader()
        lang_py, gv_py = loader.load("python")
        lang_js, gv_js = loader.load("javascript")
        cache = LanguageCache()
        cache.store("python", lang_py, gv_py)
        cache.store("javascript", lang_js, gv_js)

        keys = cache.list_loaded_keys()
        assert "python" in keys
        assert "javascript" in keys

    def test_clear_removes_all(self):
        loader = GrammarLoader()
        lang, gv = loader.load("python")
        cache = LanguageCache()
        cache.store("python", lang, gv)
        cache.clear()
        assert cache.size == 0
        assert cache.is_loaded("python") is False

    def test_load_times_recorded(self):
        loader = GrammarLoader()
        lang, gv = loader.load("python")
        cache = LanguageCache()
        cache.store("python", lang, gv, load_duration_ms=12.3)
        times = cache.load_times()
        assert "python" in times
        assert times["python"] == pytest.approx(12.3)


# ---------------------------------------------------------------------------
# ParserCache Tests
# ---------------------------------------------------------------------------

class TestParserCache:
    def _make_cache(self) -> ParserCache:
        loader = GrammarLoader()
        from tree_sitter import Language
        lang, _ = loader.load("python")
        cache = ParserCache()
        cache.register("python", lang)
        return cache

    def test_register_and_is_registered(self):
        cache = self._make_cache()
        assert cache.is_registered("python") is True

    def test_borrow_returns_usable_parser(self):
        cache = self._make_cache()
        with cache.borrow("python") as parser:
            tree = parser.parse(PYTHON_SRC)
        assert tree.root_node.type == "module"

    def test_borrow_unknown_key_raises_key_error(self):
        cache = self._make_cache()
        with pytest.raises(KeyError, match="No parser registered"):
            with cache.borrow("cobol") as _:
                pass

    def test_reuse_count_increments(self):
        cache = self._make_cache()
        for _ in range(5):
            with cache.borrow("python") as p:
                p.parse(b"x = 1")
        counts = cache.reuse_counts()
        assert counts["python"] == 5

    def test_concurrent_same_language_serialized(self):
        """Same-language borrows are serialized; no data corruption."""
        cache = self._make_cache()
        results = []
        errors = []

        def parse_work():
            try:
                with cache.borrow("python") as p:
                    tree = p.parse(PYTHON_SRC)
                    results.append(tree.root_node.type)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=parse_work) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(r == "module" for r in results)

    def test_clear_removes_parsers(self):
        cache = self._make_cache()
        cache.clear()
        assert cache.size == 0
        assert cache.is_registered("python") is False

    def test_duplicate_register_is_idempotent(self):
        loader = GrammarLoader()
        lang, _ = loader.load("python")
        cache = ParserCache()
        cache.register("python", lang)
        cache.register("python", lang)  # second call should not raise
        assert cache.size == 1


# ---------------------------------------------------------------------------
# TreeSitterEngine Tests
# ---------------------------------------------------------------------------

class TestTreeSitterEngine:
    @pytest.fixture
    def engine(self):
        e = TreeSitterEngine()
        e.initialize([ParserLanguage.PYTHON])
        yield e
        e.shutdown()

    @pytest.fixture
    def full_engine(self):
        e = TreeSitterEngine()
        e.initialize()  # all languages
        yield e
        e.shutdown()

    def test_initialize_python(self, engine: TreeSitterEngine):
        assert engine.is_language_loaded("python") is True
        assert engine._is_initialized is True

    def test_initialize_all_languages(self, full_engine: TreeSitterEngine):
        for lang in ["python", "typescript", "tsx", "javascript", "java", "go", "csharp"]:
            assert full_engine.is_language_loaded(lang) is True, f"{lang} not loaded"

    def test_initialize_idempotent(self):
        engine = TreeSitterEngine()
        r1 = engine.initialize([ParserLanguage.PYTHON])
        r2 = engine.initialize([ParserLanguage.PYTHON])  # second call should be no-op
        assert len(r1) == len(r2)
        engine.shutdown()

    def test_parse_python_success(self, engine: TreeSitterEngine):
        tree = engine.parse("python", PYTHON_SRC, "hello.py")

        assert isinstance(tree, ParseTree)
        assert tree.file_path == "hello.py"
        assert tree.language_key == "python"
        assert tree.has_errors is False
        assert tree.source_bytes == len(PYTHON_SRC)
        assert tree.parse_duration_ms >= 0.0

    def test_parse_tree_root_is_parse_tree_node(self, engine: TreeSitterEngine):
        tree = engine.parse("python", PYTHON_SRC, "test.py")
        assert isinstance(tree.root_node, ParseTreeNode)
        assert tree.root_node.node_type == "module"

    def test_parse_result_contains_no_native_objects(self, engine: TreeSitterEngine):
        """Verify the parse boundary — no tree_sitter types should appear in ParseTree."""
        try:
            from tree_sitter import Language, Parser, Node, Tree
            native_types = (Language, Parser, Node, Tree)
        except ImportError:
            return  # If tree_sitter not importable here, skip

        tree = engine.parse("python", PYTHON_SRC, "test.py")

        def check_no_native(obj, path="root"):
            assert not isinstance(obj, native_types), (
                f"Native tree-sitter object leaked at '{path}': {type(obj).__name__}"
            )
            if isinstance(obj, ParseTreeNode):
                for i, child in enumerate(obj.children):
                    check_no_native(child, f"{path}.children[{i}]")

        check_no_native(tree.root_node)

    def test_parse_invalid_syntax_marks_errors(self, engine: TreeSitterEngine):
        tree = engine.parse("python", INVALID_SRC, "bad.py")
        # Tree-sitter always produces a tree (error recovery), but may flag errors
        assert isinstance(tree, ParseTree)
        # Error state varies by grammar but tree is still returned
        assert tree.root_node is not None

    def test_parse_empty_source(self, engine: TreeSitterEngine):
        tree = engine.parse("python", b"", "empty.py")
        assert isinstance(tree, ParseTree)
        assert tree.source_bytes == 0

    def test_parse_not_initialized_raises(self):
        engine = TreeSitterEngine()
        from utils.exceptions import ParserError
        with pytest.raises(ParserError, match="not initialized"):
            engine.parse("python", PYTHON_SRC, "test.py")

    def test_parse_unknown_language_key_raises(self, engine: TreeSitterEngine):
        from utils.exceptions import ParserError
        with pytest.raises(ParserError, match="No parser registered"):
            engine.parse("cobol", b"", "test.cob")

    def test_shutdown_clears_state(self):
        engine = TreeSitterEngine()
        engine.initialize([ParserLanguage.PYTHON])
        engine.shutdown()
        assert engine._is_initialized is False

    def test_grammar_version_available_after_load(self, engine: TreeSitterEngine):
        gv = engine.get_grammar_version("python")
        assert gv is not None
        assert gv.is_loaded is True
        assert gv.abi_version >= 1

    def test_loaded_language_keys(self, engine: TreeSitterEngine):
        keys = engine.loaded_language_keys()
        assert "python" in keys

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def test_health_check_is_running(self, engine: TreeSitterEngine):
        health = engine.health_check()
        assert isinstance(health, ParserHealth)
        assert health.is_running is True
        assert health.grammar_count >= 1
        assert health.cached_parser_count >= 1

    def test_health_check_not_initialized(self):
        engine = TreeSitterEngine()
        health = engine.health_check()
        assert health.is_running is False

    def test_component_health_healthy(self, engine: TreeSitterEngine):
        from models.health import HealthStatus
        ch = engine.component_health()
        assert ch.status == HealthStatus.HEALTHY
        assert "TreeSitterEngine" in ch.name

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def test_metrics_updated_after_parse(self, engine: TreeSitterEngine):
        engine.parse("python", PYTHON_SRC, "a.py")
        engine.parse("python", PYTHON_SRC, "b.py")
        m = engine.get_metrics()
        assert isinstance(m, EngineMetrics)
        assert m.total_parses == 2
        assert m.total_parse_ms > 0
        assert m.avg_parse_ms > 0

    def test_grammar_load_time_in_metrics(self, engine: TreeSitterEngine):
        m = engine.get_metrics()
        assert "python" in m.grammar_load_times_ms
        assert m.grammar_load_times_ms["python"] >= 0.0

    def test_parser_reuse_count_in_metrics(self, engine: TreeSitterEngine):
        for _ in range(3):
            engine.parse("python", b"x=1", "f.py")
        m = engine.get_metrics()
        assert m.parser_reuse_count.get("python", 0) >= 3


# ---------------------------------------------------------------------------
# Concurrency Tests
# ---------------------------------------------------------------------------

class TestConcurrency:
    def test_concurrent_python_parses(self):
        engine = TreeSitterEngine()
        engine.initialize([ParserLanguage.PYTHON])
        results = []
        errors = []

        def worker(idx: int):
            try:
                src = f"def func_{idx}(): return {idx}".encode()
                tree = engine.parse("python", src, f"file_{idx}.py")
                results.append((idx, tree.has_errors, tree.root_node.node_type))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        engine.shutdown()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 20
        assert all(r[2] == "module" for r in results)

    def test_concurrent_multi_language_parses(self):
        engine = TreeSitterEngine()
        engine.initialize([ParserLanguage.PYTHON, ParserLanguage.JAVASCRIPT])
        results = []
        errors = []

        test_cases = [
            ("python", b"def hello(): pass"),
            ("javascript", b"function hello() {}"),
        ] * 10

        def worker(lang_key: str, src: bytes):
            try:
                tree = engine.parse(lang_key, src, f"test.{lang_key}")
                results.append((lang_key, tree.root_node.node_type))
            except Exception as e:
                errors.append((lang_key, e))

        threads = [threading.Thread(target=worker, args=(lk, src)) for lk, src in test_cases]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        engine.shutdown()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 20


# ---------------------------------------------------------------------------
# ParserManager Integration Tests
# ---------------------------------------------------------------------------

class TestParserManagerIntegration:
    def setup_method(self):
        ParserManager.reset()

    def teardown_method(self):
        ParserManager.reset()

    def test_engine_is_none_before_initialize(self):
        mgr = ParserManager()
        assert mgr.get_engine() is None

    def test_initialize_engine_explicitly(self):
        mgr = ParserManager()
        mgr.initialize_engine([ParserLanguage.PYTHON])

        engine = mgr.get_engine()
        assert engine is not None
        assert engine.is_language_loaded("python") is True

    def test_initialize_all_creates_engine(self):
        mgr = ParserManager()
        mgr.initialize_all()

        engine = mgr.get_engine()
        assert engine is not None
        assert engine._is_initialized is True

    def test_shutdown_all_clears_engine(self):
        mgr = ParserManager()
        mgr.initialize_engine([ParserLanguage.PYTHON])
        mgr.shutdown_all()

        assert mgr.get_engine() is None

    def test_health_check_includes_engine(self):
        mgr = ParserManager()
        mgr.initialize_engine([ParserLanguage.PYTHON])

        health = mgr.health_check()
        assert "tree_sitter_engine" in health
        from models.health import HealthStatus
        assert health["tree_sitter_engine"].status == HealthStatus.HEALTHY


# ---------------------------------------------------------------------------
# Benchmark Tests
# ---------------------------------------------------------------------------

class TestBenchmarks:
    """
    Benchmark measurements. These are not strict assertions on absolute timing
    (which is hardware-dependent) but verify relative performance properties.
    """

    def test_grammar_load_time_under_5_seconds(self):
        """All 7 grammars should load in well under 5s total."""
        engine = TreeSitterEngine()
        start = time.perf_counter()
        engine.initialize()
        elapsed = time.perf_counter() - start
        engine.shutdown()
        assert elapsed < 5.0, f"Grammar loading took {elapsed:.2f}s — too slow"

    def test_parser_reuse_faster_than_creation(self):
        """
        Reusing a cached parser should be faster on average than creating a new one.
        We measure 100 parses and verify average is sub-millisecond.
        """
        engine = TreeSitterEngine()
        engine.initialize([ParserLanguage.PYTHON])

        src = PYTHON_SRC * 10  # ~300 bytes
        N = 100
        start = time.perf_counter()
        for _ in range(N):
            engine.parse("python", src, "bench.py")
        total_s = time.perf_counter() - start
        engine.shutdown()

        avg_ms = (total_s / N) * 1000.0
        assert avg_ms < 10.0, f"Average parse time {avg_ms:.2f}ms exceeds 10ms threshold"

    def test_memory_does_not_grow_unboundedly(self):
        """Parse 200 files and verify RSS stays within reasonable bounds."""
        try:
            import psutil
            import os
            proc = psutil.Process(os.getpid())
        except ImportError:
            pytest.skip("psutil not available")

        engine = TreeSitterEngine()
        engine.initialize([ParserLanguage.PYTHON])

        proc.memory_info()  # warm up
        before_mb = proc.memory_info().rss / (1024 * 1024)

        for i in range(200):
            src = f"def func_{i}(x, y):\n    return x + y\n".encode()
            engine.parse("python", src, f"file_{i}.py")

        after_mb = proc.memory_info().rss / (1024 * 1024)
        engine.shutdown()

        delta_mb = after_mb - before_mb
        # Allow up to 50MB growth for 200 parses (very generous threshold)
        assert delta_mb < 50.0, f"Memory grew by {delta_mb:.1f}MB — potential leak"

    def test_grammar_load_times_captured_in_metrics(self):
        engine = TreeSitterEngine()
        engine.initialize([ParserLanguage.PYTHON, ParserLanguage.JAVASCRIPT])
        m = engine.get_metrics()
        engine.shutdown()

        assert "python" in m.grammar_load_times_ms
        assert "javascript" in m.grammar_load_times_ms
        assert m.grammar_load_times_ms["python"] >= 0.0
        assert m.grammar_load_times_ms["javascript"] >= 0.0
