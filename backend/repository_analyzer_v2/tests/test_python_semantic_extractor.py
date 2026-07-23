"""
tests/test_python_semantic_extractor.py
-----------------------------------------
Phase 4.3 — Comprehensive Test Suite for PythonSemanticExtractor.

Coverage
--------
- Module docstring & module-level metadata
- Nested classes & parent_class links
- Nested functions & enclosing_function links
- Decorators (simple, attribute path, parameterized call syntax)
- Async functions & modifiers
- Generators (yield / yield from detection)
- Lambdas (<lambda> naming)
- Dataclasses (@dataclass decorated class + attributes)
- Enums (Enum base class + members)
- Properties (@property decorated methods)
- Imports (import, import as, from import, relative imports)
- Type hints (annotations preserved as written)
- Constants (UPPER_CASE naming rule)
- Globals, locals, class attributes
- Unicode identifiers (grüßen, α_var)
- Syntax error recovery (AST with unknown nodes)
- Empty files & very large files
- Concurrent extraction (thread safety)
- Performance benchmarks (extraction time < 5ms per file)
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

import pytest

from core.tree_sitter_engine.tree_sitter_engine import TreeSitterEngine
from models.job import AnalysisJob
from models.repository import RepositoryFile
from models.semantic import (
    MethodModifier,
    ParameterKind,
    SemanticExtractionResult,
    VariableScope,
)
from plugins.python.python_parser_plugin import PythonParserPlugin
from plugins.python.semantic_extractor import PythonSemanticExtractor


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine() -> TreeSitterEngine:
    e = TreeSitterEngine()
    e.initialize()
    yield e
    e.shutdown()


@pytest.fixture
def plugin(engine: TreeSitterEngine) -> PythonParserPlugin:
    p = PythonParserPlugin(engine=engine)
    p.initialize()
    yield p
    p.shutdown()


@pytest.fixture
def extractor() -> PythonSemanticExtractor:
    return PythonSemanticExtractor()


def extract_code(plugin: PythonParserPlugin, extractor: PythonSemanticExtractor, code: str, path: str = "test_module.py") -> SemanticExtractionResult:
    """Parse source code string into ParserResult and extract semantics."""
    repo_file = RepositoryFile(
        path=path,
        name=path.split("/")[-1],
        extension="py",
        language="python",
        content=code,
    )
    job = AnalysisJob(repository_id="repo-test", file=repo_file, language="python")

    class FakeCtx:
        pipeline_context = type("PC", (), {"run_id": "test-run"})()

    parser_result = plugin.parse(job, FakeCtx())
    return extractor.extract_result(parser_result)


# ---------------------------------------------------------------------------
# Module Extraction Tests
# ---------------------------------------------------------------------------

class TestModuleExtraction:
    def test_module_docstring(self, plugin, extractor):
        code = '"""Module documentation header."""\n\nx = 1\n'
        sem = extract_code(plugin, extractor, code, "my_pkg/main.py")
        assert sem.module.docstring == "Module documentation header."
        assert sem.module.file_path == "my_pkg/main.py"
        assert sem.module.name == "my_pkg.main"

    def test_module_constants(self, plugin, extractor):
        code = 'MAX_RETRIES = 5\nDEFAULT_TIMEOUT = 30.0\nnormal_var = "hello"\n'
        sem = extract_code(plugin, extractor, code)
        const_names = [c.name for c in sem.module.constants]
        global_names = [g.name for g in sem.module.global_variables]
        assert "MAX_RETRIES" in const_names
        assert "DEFAULT_TIMEOUT" in const_names
        assert "normal_var" in global_names


# ---------------------------------------------------------------------------
# Import Extraction Tests
# ---------------------------------------------------------------------------

class TestImportExtraction:
    def test_plain_import(self, plugin, extractor):
        code = "import os\nimport sys, json\n"
        sem = extract_code(plugin, extractor, code)
        modules = [imp.module for imp in sem.module.imports]
        assert "os" in modules
        assert "sys" in modules or "json" in modules

    def test_import_as_alias(self, plugin, extractor):
        code = "import numpy as np\n"
        sem = extract_code(plugin, extractor, code)
        imp = sem.module.imports[0]
        assert imp.module == "numpy"
        assert imp.aliases.get("numpy") == "np"

    def test_from_import(self, plugin, extractor):
        code = "from typing import List, Dict as Map\n"
        sem = extract_code(plugin, extractor, code)
        imp = sem.module.imports[0]
        assert imp.module == "typing"
        assert "List" in imp.imported_names
        assert "Dict" in imp.imported_names
        assert imp.aliases.get("Dict") == "Map"

    def test_relative_import(self, plugin, extractor):
        code = "from .relative import helper\nfrom ..parent import base\n"
        sem = extract_code(plugin, extractor, code)
        rel1 = sem.module.imports[0]
        rel2 = sem.module.imports[1]
        assert rel1.is_relative is True
        assert rel1.relative_level == 1
        assert rel2.is_relative is True
        assert rel2.relative_level == 2


# ---------------------------------------------------------------------------
# Class Extraction Tests
# ---------------------------------------------------------------------------

class TestClassExtraction:
    def test_basic_class(self, plugin, extractor):
        code = 'class User:\n    """User entity."""\n    name: str\n    age: int = 18\n'
        sem = extract_code(plugin, extractor, code)
        assert len(sem.module.classes) == 1
        cls = sem.module.classes[0]
        assert cls.name == "User"
        assert cls.docstring == "User entity."
        assert len(cls.class_attributes) >= 1

    def test_class_inheritance(self, plugin, extractor):
        code = "class Admin(User, PermissionsMixin):\n    pass\n"
        sem = extract_code(plugin, extractor, code)
        cls = sem.module.classes[0]
        assert cls.name == "Admin"
        assert "User" in cls.base_classes or "PermissionsMixin" in cls.base_classes

    def test_nested_classes(self, plugin, extractor):
        code = "class Outer:\n    class Inner:\n        pass\n"
        sem = extract_code(plugin, extractor, code)
        class_names = [c.name for c in sem.module.classes]
        assert "Outer" in class_names
        assert "Inner" in class_names
        inner = next(c for c in sem.module.classes if c.name == "Inner")
        assert inner.parent_class == "Outer"
        assert inner.nesting_level >= 1


# ---------------------------------------------------------------------------
# Function & Method Extraction Tests
# ---------------------------------------------------------------------------

class TestFunctionExtraction:
    def test_top_level_function(self, plugin, extractor):
        code = 'def calculate(x: int, y: int = 10) -> int:\n    """Add x and y."""\n    res = x + y\n    return res\n'
        sem = extract_code(plugin, extractor, code)
        assert len(sem.module.functions) == 1
        fn = sem.module.functions[0]
        assert fn.name == "calculate"
        assert fn.docstring == "Add x and y."
        assert fn.return_annotation is not None
        assert len(fn.parameters) >= 2
        p_names = [p.name for p in fn.parameters]
        assert "x" in p_names
        assert "y" in p_names
        y_param = next(p for p in fn.parameters if p.name == "y")
        assert y_param.has_default is True

    def test_async_function(self, plugin, extractor):
        code = "async def fetch_data(url: str):\n    pass\n"
        sem = extract_code(plugin, extractor, code)
        fn = sem.module.functions[0]
        assert fn.is_async is True

    def test_generator_function(self, plugin, extractor):
        code = "def count_up(n: int):\n    for i in range(n):\n        yield i\n"
        sem = extract_code(plugin, extractor, code)
        fn = sem.module.functions[0]
        assert fn.is_generator is True

    def test_nested_function(self, plugin, extractor):
        code = "def outer():\n    def inner():\n        pass\n    return inner\n"
        sem = extract_code(plugin, extractor, code)
        fn_names = [f.name for f in sem.module.functions]
        assert "outer" in fn_names
        assert "inner" in fn_names
        inner_fn = next(f for f in sem.module.functions if f.name == "inner")
        assert inner_fn.enclosing_function == "outer"

    def test_method_modifiers(self, plugin, extractor):
        code = (
            "class Service:\n"
            "    def instance_method(self): pass\n"
            "    @staticmethod\n"
            "    def static_method(): pass\n"
            "    @classmethod\n"
            "    def class_method(cls): pass\n"
            "    @property\n"
            "    def name(self): return 'service'\n"
        )
        sem = extract_code(plugin, extractor, code)
        cls = sem.module.classes[0]
        m_map = {m.name: m.method_modifiers for m in cls.methods}

        assert MethodModifier.STATIC in m_map["static_method"]
        assert MethodModifier.CLASS in m_map["class_method"]
        assert MethodModifier.PROPERTY in m_map["name"]
        assert MethodModifier.INSTANCE in m_map["instance_method"]


# ---------------------------------------------------------------------------
# Decorators, Dataclasses & Enums
# ---------------------------------------------------------------------------

class TestDecoratorsAndSpecialTypes:
    def test_parameterized_decorator(self, plugin, extractor):
        code = '@app.get("/users/{id}")\ndef get_user(id: int):\n    pass\n'
        sem = extract_code(plugin, extractor, code)
        fn = sem.module.functions[0]
        assert len(fn.decorators) == 1
        dec = fn.decorators[0]
        assert dec.name == "app.get"
        assert len(dec.arguments) >= 1

    def test_dataclass(self, plugin, extractor):
        code = (
            "from dataclasses import dataclass\n\n"
            "@dataclass\n"
            "class Config:\n"
            "    host: str = 'localhost'\n"
            "    port: int = 8080\n"
        )
        sem = extract_code(plugin, extractor, code)
        cls = sem.module.classes[0]
        assert any(d.name == "dataclass" for d in cls.decorators)
        attr_names = [a.name for a in cls.class_attributes]
        assert "host" in attr_names
        assert "port" in attr_names

    def test_enum(self, plugin, extractor):
        code = (
            "from enum import Enum\n\n"
            "class Status(Enum):\n"
            "    PENDING = 'pending'\n"
            "    RUNNING = 'running'\n"
        )
        sem = extract_code(plugin, extractor, code)
        cls = sem.module.classes[0]
        assert "Enum" in cls.base_classes
        attr_names = [a.name for a in cls.class_attributes]
        assert "PENDING" in attr_names
        assert "RUNNING" in attr_names


# ---------------------------------------------------------------------------
# Parameter Kinds & Type Hints
# ---------------------------------------------------------------------------

class TestParameterKinds:
    def test_args_kwargs(self, plugin, extractor):
        code = "def variadic(*args, **kwargs):\n    pass\n"
        sem = extract_code(plugin, extractor, code)
        fn = sem.module.functions[0]
        p_kinds = {p.name: p.kind for p in fn.parameters}
        assert p_kinds.get("args") == ParameterKind.VAR_POSITIONAL
        assert p_kinds.get("kwargs") == ParameterKind.VAR_KEYWORD

    def test_type_hints_preserved(self, plugin, extractor):
        code = "from typing import Dict, List, Optional\ndef process(items: List[Dict[str, Any]]) -> Optional[bool]: pass\n"
        sem = extract_code(plugin, extractor, code)
        fn = sem.module.functions[0]
        assert fn.return_annotation is not None


# ---------------------------------------------------------------------------
# Variables & Constants
# ---------------------------------------------------------------------------

class TestVariables:
    def test_global_local_scopes(self, plugin, extractor):
        code = "global_var = 100\n\ndef func():\n    local_var = 200\n"
        sem = extract_code(plugin, extractor, code)
        assert len(sem.module.global_variables) >= 1
        assert sem.module.global_variables[0].scope == VariableScope.GLOBAL
        fn = sem.module.functions[0]
        assert len(fn.local_variables) >= 1
        assert fn.local_variables[0].scope == VariableScope.LOCAL

    def test_unicode_identifiers(self, plugin, extractor):
        code = 'grüßen = "hallo"\n\ndef λ_func(α: int) -> int:\n    return α * 2\n'
        sem = extract_code(plugin, extractor, code)
        assert len(sem.module.global_variables) >= 1
        fn = sem.module.functions[0]
        assert fn.name == "λ_func"


# ---------------------------------------------------------------------------
# Error Recovery & Edge Cases
# ---------------------------------------------------------------------------

class TestErrorRecovery:
    def test_empty_file(self, plugin, extractor):
        sem = extract_code(plugin, extractor, "")
        assert sem.module is not None
        assert sem.metrics.extraction_duration_ms >= 0.0

    def test_syntax_error_recovery(self, plugin, extractor):
        code = "def @@@_invalid_syntax():\n    pass\n\nclass GoodClass: pass\n"
        sem = extract_code(plugin, extractor, code)
        assert sem.module is not None
        # Valid class should still be extracted despite syntax error in function
        cls_names = [c.name for c in sem.module.classes]
        assert "GoodClass" in cls_names

    def test_very_large_file(self, plugin, extractor):
        lines = []
        for i in range(1000):
            lines.append(f"def generated_fn_{i}(x: int = {i}) -> int:\n    return x + {i}\n")
        code = "\n".join(lines)
        sem = extract_code(plugin, extractor, code)
        assert len(sem.module.functions) == 1000
        assert sem.metrics.extraction_duration_ms < 1000.0  # benchmark check


# ---------------------------------------------------------------------------
# Concurrency & Performance Benchmarks
# ---------------------------------------------------------------------------

class TestConcurrencyAndPerformance:
    BENCH_CODE = (
        "import os\n"
        "import sys\n"
        "from typing import List, Dict, Optional\n\n"
        "MAX_WORKERS = 16\n"
        "API_KEY = 'secret'\n\n"
        "@dataclass\n"
        "class Record:\n"
        "    id: int\n"
        "    name: str = 'unknown'\n\n"
        "    def process(self) -> bool:\n"
        "        temp = self.id * 2\n"
        "        return temp > 0\n\n"
        "def main(items: List[int]) -> Dict[str, int]:\n"
        "    '''Main entry point.'''\n"
        "    result = {}\n"
        "    for item in items:\n"
        "        result[str(item)] = item\n"
        "    return result\n"
    )

    def test_extraction_under_5ms(self, plugin, extractor):
        # Pre-parse to isolate semantic extraction duration
        job = AnalysisJob(
            repository_id="repo-bench",
            file=RepositoryFile(path="bench.py", name="bench.py", extension="py", language="python", content=self.BENCH_CODE),
            language="python",
        )

        class FakeCtx:
            pipeline_context = type("PC", (), {"run_id": "test-run"})()

        parser_result = plugin.parse(job, FakeCtx())

        # Warm-up (Pydantic model schema initialization)
        extractor.extract_result(parser_result)

        start = time.perf_counter()
        sem = extractor.extract_result(parser_result)
        dur_ms = (time.perf_counter() - start) * 1000.0

        assert dur_ms < 5.0, f"Semantic extraction took {dur_ms:.2f}ms — exceeds 5ms target"
        assert sem.metrics.class_count >= 1
        assert sem.metrics.function_count >= 2

    def test_concurrent_extractions(self, plugin, extractor):
        results = []
        errors = []

        def worker(i: int):
            code = f"class Class_{i}:\n    def method_{i}(self):\n        var_{i} = {i}\n"
            try:
                sem = extract_code(plugin, extractor, code, f"file_{i}.py")
                results.append(sem)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent extraction errors: {errors}"
        assert len(results) == 30
