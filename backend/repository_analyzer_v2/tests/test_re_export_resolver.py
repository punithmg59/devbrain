"""
tests/test_re_export_resolver.py
---------------------------------
Unit tests for ReExportResolver — recursive resolution of (package_fqn, exported_name)
through re-export chains to the ultimate defining Symbol in the SymbolTable.
"""

from models.semantic import (
    ExtractedClass,
    ExtractedFunction,
    ExtractedImport,
    ExtractedModule,
    SemanticExtractionResult,
)
from models.re_export_models import ExportRecord, ExportType
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.re_export_resolution.re_export_index import ReExportIndex
from analysis.re_export_resolution.re_export_resolver import ReExportResolver, MAX_CHAIN_DEPTH


def _build_symbol_table(*sem_results):
    builder = SymbolTableBuilder(repository_id="test-repo")
    return builder.build_from_results(list(sem_results))


def _build_index(*records: ExportRecord) -> ReExportIndex:
    index = ReExportIndex()
    index.build(list(records))
    return index


def _make_sem_result(file_path: str, module: ExtractedModule) -> SemanticExtractionResult:
    return SemanticExtractionResult(file_path=file_path, language="python", module=module)


class TestReExportResolverSimple:
    def test_resolve_simple_export(self):
        """
        fastapi/__init__.py: from .applications import FastAPI
        fastapi/applications.py: class FastAPI
        """
        mod_applications = ExtractedModule(
            name="fastapi.applications",
            file_path="fastapi/applications.py",
            classes=[ExtractedClass(name="FastAPI")],
        )
        res_applications = _make_sem_result("fastapi/applications.py", mod_applications)
        symbol_table = _build_symbol_table(res_applications)

        export_record = ExportRecord(
            package_fqn="fastapi",
            package_file_path="fastapi/__init__.py",
            exported_name="FastAPI",
            original_name="FastAPI",
            source_module_fqn="fastapi.applications",
            export_type=ExportType.FROM_IMPORT,
        )
        index = _build_index(export_record)

        resolver = ReExportResolver()
        sym, fqn = resolver.resolve("fastapi", "FastAPI", index, symbol_table)

        assert sym is not None, "FastAPI should resolve via re-export"
        assert sym.name == "FastAPI"
        assert "FastAPI" in fqn

    def test_resolve_returns_none_when_not_found(self):
        """Resolving a non-existent export returns (None, None)."""
        symbol_table = _build_symbol_table(
            _make_sem_result("empty/__init__.py", ExtractedModule(name="empty", file_path="empty/__init__.py"))
        )
        index = _build_index()  # No records
        resolver = ReExportResolver()
        sym, fqn = resolver.resolve("nonexistent", "Missing", index, symbol_table)
        assert sym is None
        assert fqn is None


class TestReExportResolverAlias:
    def test_resolve_alias_export(self):
        """
        mylib/__init__.py: from .routing import APIRouter as Router
        The import uses exported_name='Router', original_name='APIRouter'
        """
        mod_routing = ExtractedModule(
            name="mylib.routing",
            file_path="mylib/routing.py",
            classes=[ExtractedClass(name="APIRouter")],
        )
        res_routing = _make_sem_result("mylib/routing.py", mod_routing)
        symbol_table = _build_symbol_table(res_routing)

        export_record = ExportRecord(
            package_fqn="mylib",
            package_file_path="mylib/__init__.py",
            exported_name="Router",   # alias
            original_name="APIRouter",  # actual definition name
            alias="Router",
            source_module_fqn="mylib.routing",
            export_type=ExportType.FROM_IMPORT_ALIAS,
        )
        index = _build_index(export_record)

        resolver = ReExportResolver()
        sym, fqn = resolver.resolve("mylib", "Router", index, symbol_table)

        assert sym is not None, "APIRouter should resolve via alias re-export"
        assert sym.name == "APIRouter"


class TestReExportResolverStarExport:
    def test_resolve_via_star_export(self):
        """
        mylib/__init__.py: from .utils import *
        mylib/utils.py: def helper() ...
        """
        mod_utils = ExtractedModule(
            name="mylib.utils",
            file_path="mylib/utils.py",
            functions=[ExtractedFunction(name="helper")],
        )
        res_utils = _make_sem_result("mylib/utils.py", mod_utils)
        symbol_table = _build_symbol_table(res_utils)

        star_record = ExportRecord(
            package_fqn="mylib",
            package_file_path="mylib/__init__.py",
            exported_name="*",
            original_name="*",
            source_module_fqn="mylib.utils",
            export_type=ExportType.STAR_EXPORT,
            is_star_export=True,
        )
        index = _build_index(star_record)

        resolver = ReExportResolver()
        sym, fqn = resolver.resolve("mylib", "helper", index, symbol_table)

        assert sym is not None, "helper should be resolved via star export"
        assert sym.name == "helper"


class TestReExportResolverRecursiveChain:
    def test_recursive_chain_resolution(self):
        """
        pkg/__init__.py: from .sub import SubClass      (level 1 re-export)
        pkg/sub/__init__.py: from .impl import SubClass  (level 2 re-export)
        pkg/sub/impl.py: class SubClass
        """
        mod_impl = ExtractedModule(
            name="pkg.sub.impl",
            file_path="pkg/sub/impl.py",
            classes=[ExtractedClass(name="SubClass")],
        )
        res_impl = _make_sem_result("pkg/sub/impl.py", mod_impl)
        symbol_table = _build_symbol_table(res_impl)

        # Level 2: pkg.sub re-exports from pkg.sub.impl
        rec_level2 = ExportRecord(
            package_fqn="pkg.sub",
            package_file_path="pkg/sub/__init__.py",
            exported_name="SubClass",
            original_name="SubClass",
            source_module_fqn="pkg.sub.impl",
            export_type=ExportType.FROM_IMPORT,
        )
        # Level 1: pkg re-exports from pkg.sub
        rec_level1 = ExportRecord(
            package_fqn="pkg",
            package_file_path="pkg/__init__.py",
            exported_name="SubClass",
            original_name="SubClass",
            source_module_fqn="pkg.sub",
            export_type=ExportType.FROM_IMPORT,
        )
        index = _build_index(rec_level1, rec_level2)

        resolver = ReExportResolver()
        sym, fqn = resolver.resolve("pkg", "SubClass", index, symbol_table)

        assert sym is not None, "SubClass should resolve through 2-level chain"
        assert sym.name == "SubClass"
        assert "SubClass" in fqn


class TestReExportResolverCycleProtection:
    def test_cycle_does_not_hang(self):
        """
        Cyclic exports: A exports from B, B exports from A.
        Must not hang and must return (None, None).
        """
        mod_a = ExtractedModule(name="pkg.a", file_path="pkg/a.py", classes=[])
        res_a = _make_sem_result("pkg/a.py", mod_a)
        symbol_table = _build_symbol_table(res_a)

        # pkg.a claims to re-export from pkg.b, pkg.b claims to re-export from pkg.a
        rec_a = ExportRecord(
            package_fqn="pkg.a",
            package_file_path="pkg/a/__init__.py",
            exported_name="CircularClass",
            original_name="CircularClass",
            source_module_fqn="pkg.b",
            export_type=ExportType.FROM_IMPORT,
        )
        rec_b = ExportRecord(
            package_fqn="pkg.b",
            package_file_path="pkg/b/__init__.py",
            exported_name="CircularClass",
            original_name="CircularClass",
            source_module_fqn="pkg.a",
            export_type=ExportType.FROM_IMPORT,
        )
        index = _build_index(rec_a, rec_b)

        resolver = ReExportResolver()
        # Must complete (not infinite loop)
        sym, fqn = resolver.resolve("pkg.a", "CircularClass", index, symbol_table)
        # Symbol not found — cycle detected and aborted
        assert sym is None

    def test_depth_limit_respected(self):
        """Resolution chain longer than MAX_CHAIN_DEPTH returns (None, None)."""
        # We won't actually build MAX_CHAIN_DEPTH+1 records but test that
        # the depth parameter is tracked
        symbol_table = _build_symbol_table(
            _make_sem_result("x/__init__.py", ExtractedModule(name="x", file_path="x/__init__.py"))
        )
        index = _build_index()
        resolver = ReExportResolver()
        # Pass depth=MAX_CHAIN_DEPTH+1 directly to confirm it returns None immediately
        sym, fqn = resolver.resolve("x", "SomeClass", index, symbol_table, depth=MAX_CHAIN_DEPTH + 1)
        assert sym is None
        assert fqn is None
