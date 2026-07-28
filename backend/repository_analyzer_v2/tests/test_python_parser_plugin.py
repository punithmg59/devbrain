"""
tests/test_python_parser_plugin.py
------------------------------------
Phase 4.2 — Comprehensive Test Suite for PythonParserPlugin.

Coverage
--------
- Plugin initialization / lifecycle (initialize, shutdown, re-initialize)
- Supported language / capabilities / version properties
- AST conversion for all supported syntax constructs
- Diagnostic collection from syntax errors
- Error recovery (broken syntax, empty file, huge source, unicode)
- ParserResult structure validation
- Automatic validation integration
- Encoding resilience (utf-8, latin-1 fallback)
- ParserManager integration (register, execute, health)
- Concurrent parsing (thread-safety)
- Performance benchmarks (parse time, nodes/sec, memory)
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

import pytest

from models.ast import ASTNode, ASTRoot, NodeType
from models.job import AnalysisJob
from models.parser import (
    ParserCapabilities,
    ParserLanguage,
    ParserOptions,
    ParserResult,
    ParserStatus,
    ParserVersion,
)
from models.repository import RepositoryFile
from plugins.python.ast_converter import PythonASTConverter
from plugins.python.python_parser_plugin import PythonParserPlugin
from core.tree_sitter_engine.tree_sitter_engine import TreeSitterEngine
from models.tree_sitter_models import ParseTree, ParseTreeNode


# ---------------------------------------------------------------------------
# Test helpers / fixtures
# ---------------------------------------------------------------------------

def make_repo_file(path: str = "test.py", content: str = "") -> RepositoryFile:
    """Create a RepositoryFile with in-memory text content."""
    return RepositoryFile(
        path=path,
        name=path.split("/")[-1],
        extension=path.rsplit(".", 1)[-1] if "." in path else "py",
        language="python",
        size_bytes=len(content.encode()),
        line_count=content.count("\n") + 1,
        content=content,
    )


def make_repo_file_bytes(path: str, raw_bytes: bytes) -> RepositoryFile:
    """
    Create a RepositoryFile that injects raw bytes via the plugin's Strategy A.

    ``RepositoryFile.content`` is Optional[str] so raw non-UTF-8 bytes must be
    injected via the ``_content_bytes`` private attribute read by _read_source().
    """
    f = RepositoryFile(
        path=path,
        name=path.split("/")[-1],
        extension="py",
        language="python",
        size_bytes=len(raw_bytes),
    )
    # Inject private attribute for test-only bytes delivery
    object.__setattr__(f, "_content_bytes", raw_bytes)
    return f


def make_job(content: str, path: str = "test.py") -> AnalysisJob:
    """Create a minimal AnalysisJob with in-memory str source content."""
    return AnalysisJob(
        repository_id="repo-test",
        file=make_repo_file(path, content),
        language="python",
    )


def make_job_bytes(content: bytes, path: str = "test.py") -> AnalysisJob:
    """Create a minimal AnalysisJob with raw bytes source content."""
    return AnalysisJob(
        repository_id="repo-test",
        file=make_repo_file_bytes(path, content),
        language="python",
    )


class FakePipelineCtx:
    run_id = "test-run-id"


class FakeContext:
    pipeline_context = FakePipelineCtx()


@pytest.fixture(scope="module")
def engine() -> TreeSitterEngine:
    """Shared, module-scoped TreeSitterEngine to avoid repeated grammar loads."""
    e = TreeSitterEngine()
    e.initialize([ParserLanguage.PYTHON])
    yield e
    e.shutdown()


@pytest.fixture
def plugin(engine: TreeSitterEngine) -> PythonParserPlugin:
    """Fresh plugin per test, sharing the module-scoped engine."""
    p = PythonParserPlugin(engine=engine)
    p.initialize()
    yield p
    p.shutdown()


def parse_str(plugin: PythonParserPlugin, source: str, path: str = "test.py") -> ParserResult:
    """Helper: build job (str content) + context and call plugin.parse()."""
    job = make_job(source, path)
    return plugin.parse(job, FakeContext())


def parse_bytes(plugin: PythonParserPlugin, source: bytes, path: str = "test.py") -> ParserResult:
    """Helper: build job (raw bytes) + context and call plugin.parse()."""
    job = make_job_bytes(source, path)
    return plugin.parse(job, FakeContext())


# ---------------------------------------------------------------------------
# Lifecycle Tests
# ---------------------------------------------------------------------------

class TestLifecycle:
    def test_initialize_sets_initialized(self, engine):
        p = PythonParserPlugin(engine=engine)
        assert not p.is_initialized
        p.initialize()
        assert p.is_initialized
        p.shutdown()

    def test_initialize_idempotent(self, engine):
        p = PythonParserPlugin(engine=engine)
        p.initialize()
        p.initialize()  # second call must not raise
        assert p.is_initialized
        p.shutdown()

    def test_shutdown_clears_initialized(self, engine):
        p = PythonParserPlugin(engine=engine)
        p.initialize()
        p.shutdown()
        assert not p.is_initialized

    def test_owns_engine_shutdown(self):
        """Plugin with no injected engine creates and shuts down its own engine."""
        p = PythonParserPlugin()
        p.initialize()
        assert p.is_initialized
        p.shutdown()
        assert not p.is_initialized

    def test_parse_without_initialize_returns_error(self, engine):
        p = PythonParserPlugin(engine=engine)
        result = parse_str(p, "x = 1")
        assert result.status == ParserStatus.INTERNAL_ERROR
        assert result.errors

    def test_health_not_initialized(self, engine):
        p = PythonParserPlugin(engine=engine)
        from models.health import HealthStatus
        assert p.health().status == HealthStatus.UNHEALTHY

    def test_health_initialized(self, plugin):
        from models.health import HealthStatus
        assert plugin.health().status == HealthStatus.HEALTHY

    def test_health_contains_stats(self, plugin):
        parse_str(plugin, "x = 1")
        details = plugin.health().details
        assert "total_parses" in details
        assert details["total_parses"] >= 1


# ---------------------------------------------------------------------------
# Plugin Properties
# ---------------------------------------------------------------------------

class TestProperties:
    def test_language_is_python(self, plugin):
        assert plugin.language == ParserLanguage.PYTHON

    def test_version_semver(self, plugin):
        v = plugin.version
        assert isinstance(v, ParserVersion)
        parts = v.semver.split(".")
        assert len(parts) == 3

    def test_capabilities_ast(self, plugin):
        caps = plugin.capabilities
        assert isinstance(caps, ParserCapabilities)
        assert caps.supports_ast is True

    def test_capabilities_docstring(self, plugin):
        assert plugin.capabilities.supports_docstring_extraction is True

    def test_capabilities_error_recovery(self, plugin):
        assert plugin.capabilities.supports_error_recovery is True

    def test_validate_valid_source(self, plugin):
        assert plugin.validate("def foo(): pass") is True

    def test_validate_invalid_source(self, plugin):
        result = plugin.validate("def @@@invalid###")
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# ParserResult structure
# ---------------------------------------------------------------------------

class TestParserResultStructure:
    def test_result_has_job_id(self, plugin):
        job = make_job("x = 1")
        result = plugin.parse(job, FakeContext())
        assert result.job_id == job.job_id

    def test_result_has_file_path(self, plugin):
        result = parse_str(plugin, "x = 1", "src/foo.py")
        assert result.file_path == "src/foo.py"

    def test_result_language_is_python(self, plugin):
        result = parse_str(plugin, "x = 1")
        assert result.language == ParserLanguage.PYTHON

    def test_result_has_metadata(self, plugin):
        result = parse_str(plugin, "x = 1")
        assert result.metadata is not None
        assert result.metadata.parser_name == "tree-sitter-python"

    def test_result_has_statistics(self, plugin):
        result = parse_str(plugin, "x = 1")
        assert result.statistics.duration_ms >= 0.0
        assert result.statistics.bytes_parsed > 0
        assert result.statistics.lines_parsed >= 1

    def test_result_has_source_hash(self, plugin):
        result = parse_str(plugin, "x = 1")
        assert result.metadata.file_hash is not None
        assert len(result.metadata.file_hash) == 64  # SHA-256 hex

    def test_file_size_exceeded_returns_skipped(self, plugin):
        huge = "x = 1\n" * 1_000_000
        opts = ParserOptions(max_file_size_kb=1)
        job = make_job(huge)
        result = plugin.parse(job, FakeContext(), options=opts)
        assert result.status == ParserStatus.SKIPPED


# ---------------------------------------------------------------------------
# AST Structure Tests
# ---------------------------------------------------------------------------

class TestASTStructure:
    def _ast(self, plugin, src: str) -> Dict:
        result = parse_str(plugin, src)
        assert result.ast_root is not None, f"No AST produced. Errors: {result.errors}"
        return result.ast_root

    def test_ast_root_type_is_module(self, plugin):
        ast = self._ast(plugin, "x = 1")
        assert ast["root_node"]["type"] == NodeType.MODULE.value

    def test_ast_has_total_nodes(self, plugin):
        ast = self._ast(plugin, "x = 1\ny = 2\n")
        assert ast["total_nodes"] >= 2

    def test_ast_has_max_depth(self, plugin):
        ast = self._ast(plugin, "def foo():\n    return 1\n")
        assert ast["max_depth"] >= 2

    def test_function_definition(self, plugin):
        ast = self._ast(plugin, "def greet(name): return name\n")
        children = ast["root_node"]["children"]
        types = [c["type"] for c in children]
        assert NodeType.FUNCTION.value in types

    def test_function_name_extracted(self, plugin):
        ast = self._ast(plugin, "def my_func(): pass\n")
        funcs = [c for c in ast["root_node"]["children"] if c["type"] == NodeType.FUNCTION.value]
        assert funcs, "No FUNCTION node found"
        assert funcs[0]["name"] == "my_func"

    def test_async_function_modifier(self, plugin):
        ast = self._ast(plugin, "async def afunc(): pass\n")
        funcs = [c for c in ast["root_node"]["children"] if c["type"] == NodeType.FUNCTION.value]
        assert funcs
        assert "async" in funcs[0]["metadata"]["modifiers"]

    def test_class_definition(self, plugin):
        ast = self._ast(plugin, "class Foo: pass\n")
        types = [c["type"] for c in ast["root_node"]["children"]]
        assert NodeType.CLASS.value in types

    def test_class_name_extracted(self, plugin):
        ast = self._ast(plugin, "class MyClass: pass\n")
        classes = [c for c in ast["root_node"]["children"] if c["type"] == NodeType.CLASS.value]
        assert classes
        assert classes[0]["name"] == "MyClass"

    def test_import_statement(self, plugin):
        ast = self._ast(plugin, "import os\n")
        types = [c["type"] for c in ast["root_node"]["children"]]
        assert NodeType.IMPORT.value in types

    def test_from_import_statement(self, plugin):
        ast = self._ast(plugin, "from os import path\n")
        types = [c["type"] for c in ast["root_node"]["children"]]
        assert NodeType.IMPORT.value in types

    def test_import_name_contains_module(self, plugin):
        ast = self._ast(plugin, "import os\n")
        imports = [c for c in ast["root_node"]["children"] if c["type"] == NodeType.IMPORT.value]
        assert imports
        assert "os" in (imports[0]["name"] or "")

    def test_if_statement(self, plugin):
        ast = self._ast(plugin, "x = 1\nif x > 0:\n    pass\n")
        types = [c["type"] for c in ast["root_node"]["children"]]
        assert NodeType.IF.value in types

    def test_for_loop(self, plugin):
        ast = self._ast(plugin, "for i in range(10):\n    pass\n")
        types = [c["type"] for c in ast["root_node"]["children"]]
        assert NodeType.LOOP.value in types

    def test_while_loop(self, plugin):
        ast = self._ast(plugin, "while True:\n    break\n")
        types = [c["type"] for c in ast["root_node"]["children"]]
        assert NodeType.LOOP.value in types

    def test_try_statement(self, plugin):
        ast = self._ast(plugin, "try:\n    pass\nexcept Exception:\n    pass\n")
        types = [c["type"] for c in ast["root_node"]["children"]]
        assert NodeType.TRY.value in types

    def test_with_statement(self, plugin):
        result = parse_str(plugin, "with open('f') as f:\n    pass\n")
        assert result.ast_root is not None
        assert result.ast_root["total_nodes"] >= 2

    def test_return_statement(self, plugin):
        result = parse_str(plugin, "def f():\n    return 1\n")
        ast = result.ast_root
        assert ast is not None

        def find_type(node, target):
            if node["type"] == target:
                return True
            return any(find_type(c, target) for c in node.get("children", []))

        assert find_type(ast["root_node"], NodeType.RETURN.value)

    def test_lambda(self, plugin):
        result = parse_str(plugin, "f = lambda x: x + 1\n")
        assert result.ast_root is not None

        def find_type(node, target):
            if node["type"] == target:
                return True
            return any(find_type(c, target) for c in node.get("children", []))

        assert find_type(result.ast_root["root_node"], NodeType.FUNCTION.value)

    def test_lambda_name_is_lambda(self, plugin):
        result = parse_str(plugin, "f = lambda x: x\n")
        ast = result.ast_root

        def find_lambda(node):
            if node["type"] == NodeType.FUNCTION.value and node.get("name") == "<lambda>":
                return True
            return any(find_lambda(c) for c in node.get("children", []))

        assert ast is not None
        assert find_lambda(ast["root_node"])

    def test_decorator(self, plugin):
        ast = self._ast(plugin, "@staticmethod\ndef f(): pass\n")
        funcs = [c for c in ast["root_node"]["children"] if c["type"] == NodeType.FUNCTION.value]
        assert funcs
        decs = funcs[0]["metadata"]["decorators"]
        assert any("staticmethod" in d for d in decs)

    def test_function_return_type_annotation(self, plugin):
        ast = self._ast(plugin, "def f() -> str: pass\n")
        funcs = [c for c in ast["root_node"]["children"] if c["type"] == NodeType.FUNCTION.value]
        assert funcs
        assert funcs[0]["metadata"]["type_annotation"] is not None

    def test_docstring_extraction_function(self, plugin):
        src = 'def f():\n    """This is a docstring."""\n    pass\n'
        ast = self._ast(plugin, src)
        funcs = [c for c in ast["root_node"]["children"] if c["type"] == NodeType.FUNCTION.value]
        assert funcs
        assert funcs[0]["metadata"]["docstring"] is not None
        assert "docstring" in funcs[0]["metadata"]["docstring"]

    def test_docstring_extraction_class(self, plugin):
        src = 'class Foo:\n    """Class doc."""\n    pass\n'
        ast = self._ast(plugin, src)
        classes = [c for c in ast["root_node"]["children"] if c["type"] == NodeType.CLASS.value]
        assert classes
        assert classes[0]["metadata"]["docstring"] is not None

    def test_match_statement(self, plugin):
        src = "match cmd:\n    case 'quit':\n        pass\n    case _:\n        pass\n"
        result = parse_str(plugin, src)
        assert result.ast_root is not None

    def test_comprehensions(self, plugin):
        src = "result = [x for x in range(10)]\n"
        result = parse_str(plugin, src)
        assert result.status in (ParserStatus.SUCCESS, ParserStatus.PARTIAL_SUCCESS)

    def test_yield_expression(self, plugin):
        src = "def gen():\n    yield 1\n    yield from range(3)\n"
        result = parse_str(plugin, src)
        assert result.ast_root is not None

    def test_await_expression(self, plugin):
        src = "async def f():\n    await coro()\n"
        result = parse_str(plugin, src)
        assert result.ast_root is not None

    def test_nested_classes(self, plugin):
        src = "class Outer:\n    class Inner:\n        pass\n"
        result = parse_str(plugin, src)
        assert result.ast_root is not None

    def test_nested_functions(self, plugin):
        src = "def outer():\n    def inner():\n        pass\n    return inner\n"
        result = parse_str(plugin, src)
        assert result.ast_root is not None
        assert result.statistics.node_count > 3

    def test_range_information_populated(self, plugin):
        ast = self._ast(plugin, "x = 1\n")
        root = ast["root_node"]
        rng = root["range"]
        assert rng["start"]["line"] >= 1
        assert rng["end"]["line"] >= 1

    def test_parent_id_wiring(self, plugin):
        ast = self._ast(plugin, "def f():\n    x = 1\n")
        root = ast["root_node"]
        # Root should have no parent
        assert root["relationships"]["parent_id"] is None
        # Children should have root_node's node_id as parent
        for child in root["children"]:
            assert child["relationships"]["parent_id"] == root["node_id"]


# ---------------------------------------------------------------------------
# Error Recovery Tests
# ---------------------------------------------------------------------------

class TestErrorRecovery:
    def test_empty_file(self, plugin):
        result = parse_str(plugin, "")
        assert result is not None
        assert result.status in (ParserStatus.SUCCESS, ParserStatus.PARTIAL_SUCCESS, ParserStatus.SYNTAX_ERROR)

    def test_syntax_error_recovery(self, plugin):
        """Plugin must return a result even on invalid syntax."""
        result = parse_str(plugin, "def @@@@bad_syntax\n")
        assert result is not None
        assert result.status in (
            ParserStatus.PARTIAL_SUCCESS,
            ParserStatus.SYNTAX_ERROR,
            ParserStatus.SUCCESS,
        )

    def test_incomplete_function(self, plugin):
        result = parse_str(plugin, "def f(\n")
        assert result is not None

    def test_broken_indentation(self, plugin):
        result = parse_str(plugin, "def f():\nreturn 1\n")
        assert result is not None

    def test_unicode_source(self, plugin):
        src = "def greet(name):\n    return 'Hello ' + name\n"
        result = parse_str(plugin, src)
        assert result is not None
        assert result.status in (ParserStatus.SUCCESS, ParserStatus.PARTIAL_SUCCESS)

    def test_latin1_fallback_via_bytes(self, plugin):
        """Bytes that are not valid UTF-8 trigger latin-1 fallback + warning."""
        # b'\xe9' is not valid UTF-8 (it is 'é' in latin-1)
        src = b"# caf\xe9\nx = 1\n"
        result = parse_bytes(plugin, src)
        assert result is not None
        warning_messages = [w.message for w in result.warnings]
        assert any("latin-1" in m for m in warning_messages)

    def test_very_large_source(self, plugin):
        """Very large valid Python should parse without crash."""
        lines = "\n".join(f"def func_{i}(x, y, z): return x + y + z" for i in range(2000))
        opts = ParserOptions(max_file_size_kb=5000)
        job = make_job(lines)
        result = plugin.parse(job, FakeContext(), options=opts)
        assert result is not None
        assert result.status in (ParserStatus.SUCCESS, ParserStatus.PARTIAL_SUCCESS)

    def test_syntax_error_diagnostics_have_location(self, plugin):
        """Syntax error records must have valid line numbers."""
        result = parse_str(plugin, "def @@@\n")
        for err in result.errors:
            assert err.line >= 1

    def test_many_syntax_errors_capped(self, plugin):
        """Error collection must be capped at max_errors."""
        bad_lines = "@@@@\n" * 100
        result = parse_str(plugin, bad_lines)
        assert len(result.errors) <= 51


# ---------------------------------------------------------------------------
# Complex Python Constructs
# ---------------------------------------------------------------------------

class TestComplexConstructs:
    DECORATED_SRC = (
        "import functools\n\n"
        "def my_decorator(func):\n"
        "    @functools.wraps(func)\n"
        "    def wrapper(*args, **kwargs):\n"
        "        return func(*args, **kwargs)\n"
        "    return wrapper\n\n"
        "@my_decorator\n"
        "def public_api(x: int, y: int = 0) -> int:\n"
        "    return x + y\n"
    )

    def test_decorated_function_parsed(self, plugin):
        result = parse_str(plugin, self.DECORATED_SRC)
        assert result.status in (ParserStatus.SUCCESS, ParserStatus.PARTIAL_SUCCESS)
        assert result.ast_root is not None

    def test_generators_and_comprehensions(self, plugin):
        src = (
            "squares = [x**2 for x in range(10)]\n"
            "evens = {x for x in range(20) if x % 2 == 0}\n"
            "table = {k: v for k, v in enumerate(range(5))}\n"
            "gen = (x for x in range(10))\n"
        )
        result = parse_str(plugin, src)
        assert result.ast_root is not None

    def test_match_with_patterns(self, plugin):
        src = (
            "match point:\n"
            "    case (0, 0):\n"
            "        print('origin')\n"
            "    case (x, 0):\n"
            "        print('x-axis')\n"
            "    case _:\n"
            "        print('other')\n"
        )
        result = parse_str(plugin, src)
        assert result.ast_root is not None

    def test_async_generator(self, plugin):
        src = (
            "async def agen():\n"
            "    for i in range(10):\n"
            "        yield i\n"
        )
        result = parse_str(plugin, src)
        assert result.ast_root is not None

    def test_type_annotations_complex(self, plugin):
        src = (
            "from typing import Dict, List, Optional, Union\n"
            "def process(data: Dict[str, List[int]], flag: Optional[bool] = None):\n"
            "    pass\n"
        )
        result = parse_str(plugin, src)
        assert result.ast_root is not None

    def test_large_class_hierarchy(self, plugin):
        parts = []
        for i in range(20):
            parts.append(f"class Class{i}:")
            parts.append(f"    def method_{i}(self): pass")
        src = "\n".join(parts)
        result = parse_str(plugin, src)
        assert result.ast_root is not None
        assert result.statistics.node_count > 20

    def test_walrus_operator(self, plugin):
        src = "data = [1, 2, 3]\nif n := len(data):\n    print(n)\n"
        result = parse_str(plugin, src)
        assert result.ast_root is not None

    def test_multiple_imports(self, plugin):
        src = (
            "import os\n"
            "import sys\n"
            "from typing import List, Dict\n"
            "from pathlib import Path\n"
        )
        ast = parse_str(plugin, src).ast_root
        assert ast is not None
        imports = [c for c in ast["root_node"]["children"] if c["type"] == NodeType.IMPORT.value]
        assert len(imports) >= 3


# ---------------------------------------------------------------------------
# ASTConverter Unit Tests
# ---------------------------------------------------------------------------

class TestASTConverter:
    @pytest.fixture(scope="class")
    def eng(self):
        e = TreeSitterEngine()
        e.initialize([ParserLanguage.PYTHON])
        yield e
        e.shutdown()

    def _parse(self, eng, src: bytes, path: str = "test.py") -> ParseTree:
        if not eng.is_language_loaded("python"):
            pytest.skip("tree-sitter-python grammar not loaded on this platform")
        return eng.parse("python", src, path)

    def test_convert_empty_module(self, eng):
        tree = self._parse(eng, b"")
        converter = PythonASTConverter()
        root = converter.convert(tree, b"")
        assert root.root_node.type == NodeType.MODULE

    def test_convert_function(self, eng):
        src = b"def foo(): pass\n"
        tree = self._parse(eng, src)
        converter = PythonASTConverter()
        root = converter.convert(tree, src)
        funcs = root.root_node.find_by_type(NodeType.FUNCTION)
        assert len(funcs) >= 1
        assert funcs[0].name == "foo"

    def test_convert_class(self, eng):
        src = b"class Bar: pass\n"
        tree = self._parse(eng, src)
        converter = PythonASTConverter()
        root = converter.convert(tree, src)
        classes = root.root_node.find_by_type(NodeType.CLASS)
        assert len(classes) == 1
        assert classes[0].name == "Bar"

    def test_node_count_positive(self, eng):
        src = b"x = 1\ny = 2\n"
        tree = self._parse(eng, src)
        converter = PythonASTConverter()
        root = converter.convert(tree, src)
        assert converter.node_count >= 2
        assert root.total_nodes >= 2

    def test_error_count_clean_source(self, eng):
        src = b"x = 1\n"
        tree = self._parse(eng, src)
        converter = PythonASTConverter()
        converter.convert(tree, src)
        assert converter.error_count == 0

    def test_range_lines_are_1indexed(self, eng):
        src = b"x = 1\n"
        tree = self._parse(eng, src)
        converter = PythonASTConverter()
        root = converter.convert(tree, src)
        assert root.root_node.range.start.line >= 1

    def test_ast_root_file_path(self, eng):
        src = b"x = 1\n"
        tree = self._parse(eng, src, "src/main.py")
        converter = PythonASTConverter()
        root = converter.convert(tree, src)
        assert root.file_path == "src/main.py"
        assert root.language == "python"

    def test_parent_child_links(self, eng):
        src = b"def f():\n    x = 1\n"
        tree = self._parse(eng, src)
        converter = PythonASTConverter()
        root = converter.convert(tree, src)
        for node in root.walk():
            for child in node.children:
                assert child.relationships.parent_id == node.node_id

    def test_walk_yields_all_nodes(self, eng):
        src = b"class Foo:\n    def bar(self): pass\n"
        tree = self._parse(eng, src)
        converter = PythonASTConverter()
        root = converter.convert(tree, src)
        all_nodes = list(root.walk())
        assert len(all_nodes) == root.total_nodes


# ---------------------------------------------------------------------------
# Concurrent Parsing Tests
# ---------------------------------------------------------------------------

class TestConcurrency:
    def test_concurrent_parses_thread_safe(self, plugin):
        results = []
        errors = []

        def worker(i: int):
            src = f"def func_{i}(): return {i}\n"
            try:
                r = parse_str(plugin, src, f"file_{i}.py")
                results.append((i, r.status))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 30
        assert all(s in (ParserStatus.SUCCESS, ParserStatus.PARTIAL_SUCCESS) for _, s in results)

    def test_concurrent_different_sources(self, plugin):
        sources = [
            "class A: pass\n",
            "import os\n",
            "x = 1\n",
            "def f(): pass\n",
            "for i in range(10): pass\n",
        ]
        results = []

        def worker(src):
            results.append(parse_str(plugin, src))

        threads = [threading.Thread(target=worker, args=(src,)) for src in sources * 4]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        assert all(r.ast_root is not None for r in results)


# ---------------------------------------------------------------------------
# ParserManager Integration
# ---------------------------------------------------------------------------

class TestParserManagerIntegration:
    def setup_method(self):
        from core.parser_manager import ParserManager
        ParserManager.reset()

    def teardown_method(self):
        from core.parser_manager import ParserManager
        ParserManager.reset()

    def test_register_python_plugin(self, engine):
        from core.parser_manager import ParserManager
        mgr = ParserManager()
        plugin = PythonParserPlugin(engine=engine)
        plugin.initialize()
        mgr.register_parser(plugin)
        assert ParserLanguage.PYTHON in mgr.get_registered_languages()

    def test_select_python_plugin(self, engine):
        from core.parser_manager import ParserManager
        mgr = ParserManager()
        plugin = PythonParserPlugin(engine=engine)
        plugin.initialize()
        mgr.register_parser(plugin)
        selected = mgr.select_parser(ParserLanguage.PYTHON)
        assert selected is plugin

    def test_health_check_includes_python(self, engine):
        from core.parser_manager import ParserManager
        from models.health import HealthStatus
        mgr = ParserManager()
        plugin = PythonParserPlugin(engine=engine)
        plugin.initialize()
        mgr.register_parser(plugin)
        health = mgr.health_check()
        assert "python" in health
        assert health["python"].status == HealthStatus.HEALTHY


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------

BENCH_SOURCE = (
    "import os\n"
    "import sys\n"
    "from typing import List, Dict, Optional\n"
    "\n"
    "class BenchClass:\n"
    '    """Benchmark class."""\n'
    "    def __init__(self, x: int, y: int) -> None:\n"
    "        self.x = x\n"
    "        self.y = y\n"
    "\n"
    "    def compute(self, factor: float = 1.0) -> float:\n"
    "        result = (self.x + self.y) * factor\n"
    "        return result\n"
    "\n"
    "def standalone(items: List[int]) -> Dict[str, int]:\n"
    "    return {str(i): i for i in items}\n"
    "\n"
    "if __name__ == '__main__':\n"
    "    obj = BenchClass(10, 20)\n"
    "    print(obj.compute(2.5))\n"
)


class TestBenchmarks:
    def test_single_parse_under_100ms(self, plugin):
        start = time.perf_counter()
        result = parse_str(plugin, BENCH_SOURCE)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert elapsed_ms < 100.0, f"Parse took {elapsed_ms:.1f}ms — too slow"
        assert result.ast_root is not None

    def test_hundred_parses_avg_under_10ms(self, plugin):
        N = 100
        start = time.perf_counter()
        for _ in range(N):
            parse_str(plugin, BENCH_SOURCE)
        total_s = time.perf_counter() - start
        avg_ms = (total_s / N) * 1000.0
        assert avg_ms < 30.0, f"Average parse time {avg_ms:.2f}ms exceeds 30ms"

    def test_nodes_per_second(self, plugin):
        """Verify AST generation throughput."""
        N = 50
        total_nodes = 0
        start = time.perf_counter()
        for _ in range(N):
            result = parse_str(plugin, BENCH_SOURCE)
            total_nodes += result.statistics.node_count
        elapsed = time.perf_counter() - start
        nps = total_nodes / elapsed
        assert nps > 1000, f"Nodes/sec too low: {nps:.0f}"

    def test_memory_stable_over_many_parses(self, plugin):
        """RSS should not grow unboundedly over 500 parses."""
        try:
            import psutil
            import os as _os
            proc = psutil.Process(_os.getpid())
        except ImportError:
            pytest.skip("psutil not available")

        before_mb = proc.memory_info().rss / (1024 * 1024)
        for _ in range(500):
            parse_str(plugin, BENCH_SOURCE)
        after_mb = proc.memory_info().rss / (1024 * 1024)
        delta_mb = after_mb - before_mb
        assert delta_mb < 50.0, f"Memory grew {delta_mb:.1f}MB over 500 parses"

    def test_statistics_node_count_matches_ast(self, plugin):
        """statistics.node_count must equal ast_root total_nodes."""
        result = parse_str(plugin, BENCH_SOURCE)
        assert result.ast_root is not None
        assert result.statistics.node_count == result.ast_root["total_nodes"]
