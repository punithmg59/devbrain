"""
tests/test_re_export_integration.py
-------------------------------------
End-to-end integration tests for Phase 4.7.1 Re-Export Symbol Resolution Engine.

Tests verify that the full ImportResolver pipeline correctly resolves symbols
that are re-exported through package __init__.py files, simulating the FastAPI
re-export pattern: `from fastapi import FastAPI`.

These tests exercise the complete pipeline:
SemanticExtractionResult → SymbolTable → ImportResolver (with Re-Export pre-pass)
→ RESOLVED_INTERNAL
"""

from models.semantic import (
    ExtractedClass,
    ExtractedFunction,
    ExtractedImport,
    ExtractedModule,
    SemanticExtractionResult,
)
from models.import_models import ImportResolutionStatus
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.import_resolution.import_resolver import ImportResolver


def _sem(file_path: str, module: ExtractedModule) -> SemanticExtractionResult:
    return SemanticExtractionResult(file_path=file_path, language="python", module=module)


class TestFastAPIPattern:
    """Simulates the exact re-export pattern that failed in the FastAPI benchmark."""

    def _build_fastapi_fixtures(self):
        """
        Minimal FastAPI-like repository fixture:

        fastapi/__init__.py:
            from .applications import FastAPI
            from .routing import APIRouter

        fastapi/applications.py:
            class FastAPI: ...

        fastapi/routing.py:
            class APIRouter: ...

        user_code.py:
            from fastapi import FastAPI
            from fastapi import APIRouter
        """
        mod_init = ExtractedModule(
            name="fastapi",
            file_path="fastapi/__init__.py",
            imports=[
                ExtractedImport(
                    module="applications",
                    imported_names=["FastAPI"],
                    is_relative=True,
                    relative_level=1,
                ),
                ExtractedImport(
                    module="routing",
                    imported_names=["APIRouter"],
                    is_relative=True,
                    relative_level=1,
                ),
            ],
        )
        mod_applications = ExtractedModule(
            name="fastapi.applications",
            file_path="fastapi/applications.py",
            classes=[ExtractedClass(name="FastAPI")],
        )
        mod_routing = ExtractedModule(
            name="fastapi.routing",
            file_path="fastapi/routing.py",
            classes=[ExtractedClass(name="APIRouter")],
        )
        mod_user = ExtractedModule(
            name="user_code",
            file_path="user_code.py",
            imports=[
                ExtractedImport(module="fastapi", imported_names=["FastAPI"]),
                ExtractedImport(module="fastapi", imported_names=["APIRouter"]),
            ],
        )

        res_init = _sem("fastapi/__init__.py", mod_init)
        res_applications = _sem("fastapi/applications.py", mod_applications)
        res_routing = _sem("fastapi/routing.py", mod_routing)
        res_user = _sem("user_code.py", mod_user)

        return [res_init, res_applications, res_routing, res_user]

    def test_fastapi_class_resolves_via_re_export(self):
        """from fastapi import FastAPI → RESOLVED_INTERNAL (not UNRESOLVED_SYMBOL)."""
        sem_results = self._build_fastapi_fixtures()

        sym_builder = SymbolTableBuilder(repository_id="test-fastapi")
        symbol_table = sym_builder.build_from_results(sem_results)

        resolver = ImportResolver(repository_id="test-fastapi")
        result = resolver.resolve_results(sem_results, symbol_table)

        # Find the resolution for `from fastapi import FastAPI`
        fastapi_resolutions = [
            (rec, result.resolutions[rec.id])
            for rec in result.imports.values()
            if rec.imported_symbol_name == "FastAPI"
            and rec.imported_module_name == "fastapi"
        ]

        assert len(fastapi_resolutions) == 1, "Expected exactly one FastAPI import"
        rec, res = fastapi_resolutions[0]
        assert res.status == ImportResolutionStatus.RESOLVED_INTERNAL, (
            f"Expected RESOLVED_INTERNAL but got {res.status}. "
            f"Error: {res.error_message}"
        )
        assert res.target_symbol_id is not None, "target_symbol_id must be set"
        assert res.target_symbol_fqn is not None, "target_symbol_fqn must be set"
        assert "FastAPI" in res.target_symbol_fqn

    def test_apirouter_resolves_via_re_export(self):
        """from fastapi import APIRouter → RESOLVED_INTERNAL."""
        sem_results = self._build_fastapi_fixtures()

        sym_builder = SymbolTableBuilder(repository_id="test-fastapi")
        symbol_table = sym_builder.build_from_results(sem_results)

        resolver = ImportResolver(repository_id="test-fastapi")
        result = resolver.resolve_results(sem_results, symbol_table)

        router_resolutions = [
            (rec, result.resolutions[rec.id])
            for rec in result.imports.values()
            if rec.imported_symbol_name == "APIRouter"
            and rec.imported_module_name == "fastapi"
        ]

        assert len(router_resolutions) == 1
        rec, res = router_resolutions[0]
        assert res.status == ImportResolutionStatus.RESOLVED_INTERNAL, (
            f"Expected RESOLVED_INTERNAL but got {res.status}. "
            f"Error: {res.error_message}"
        )
        assert res.target_symbol_id is not None
        assert "APIRouter" in res.target_symbol_fqn

    def test_metrics_count_internal_resolved(self):
        """Re-export resolutions contribute to metrics.resolved_internal, not unresolved."""
        sem_results = self._build_fastapi_fixtures()
        sym_builder = SymbolTableBuilder(repository_id="test-fastapi")
        symbol_table = sym_builder.build_from_results(sem_results)

        resolver = ImportResolver(repository_id="test-fastapi")
        result = resolver.resolve_results(sem_results, symbol_table)

        # FastAPI and APIRouter from user_code.py must count as resolved_internal
        assert result.metrics.resolved_internal >= 2, (
            f"Expected at least 2 internal resolutions (FastAPI + APIRouter from user_code.py), "
            f"got {result.metrics.resolved_internal}"
        )

        # User-code imports (from fastapi import X) must all be RESOLVED_INTERNAL
        user_code_resolutions = [
            result.resolutions[rec.id]
            for rec in result.imports.values()
            if rec.source_file_path == "user_code.py"
        ]
        assert all(
            r.status == ImportResolutionStatus.RESOLVED_INTERNAL
            for r in user_code_resolutions
        ), (
            "All user_code.py imports should resolve as RESOLVED_INTERNAL via re-export. "
            f"Got: {[(r.status, r.error_message) for r in user_code_resolutions]}"
        )



class TestAliasedReExport:
    def test_aliased_re_export_resolved(self):
        """
        pkg/__init__.py: from .core import BaseClass as Base
        user.py: from pkg import Base
        """
        mod_init = ExtractedModule(
            name="pkg",
            file_path="pkg/__init__.py",
            imports=[
                ExtractedImport(
                    module="core",
                    imported_names=["BaseClass"],
                    aliases={"BaseClass": "Base"},
                    is_relative=True,
                    relative_level=1,
                )
            ],
        )
        mod_core = ExtractedModule(
            name="pkg.core",
            file_path="pkg/core.py",
            classes=[ExtractedClass(name="BaseClass")],
        )
        mod_user = ExtractedModule(
            name="user",
            file_path="user.py",
            imports=[
                ExtractedImport(module="pkg", imported_names=["Base"]),
            ],
        )

        sem_results = [
            _sem("pkg/__init__.py", mod_init),
            _sem("pkg/core.py", mod_core),
            _sem("user.py", mod_user),
        ]

        sym_builder = SymbolTableBuilder(repository_id="test-alias")
        symbol_table = sym_builder.build_from_results(sem_results)

        resolver = ImportResolver(repository_id="test-alias")
        result = resolver.resolve_results(sem_results, symbol_table)

        base_resolutions = [
            (rec, result.resolutions[rec.id])
            for rec in result.imports.values()
            if rec.imported_symbol_name == "Base"
            and rec.imported_module_name == "pkg"
        ]

        assert len(base_resolutions) == 1
        rec, res = base_resolutions[0]
        assert res.status == ImportResolutionStatus.RESOLVED_INTERNAL, (
            f"Expected RESOLVED_INTERNAL for aliased re-export 'Base', got {res.status}"
        )
        assert res.target_symbol_id is not None


class TestExistingResolutionRegressions:
    """Ensure existing resolution behavior is not broken by Phase 4.7.1 changes."""

    def test_direct_symbol_still_resolved(self):
        """Direct symbols in target module still resolve without going through re-export."""
        mod_auth = ExtractedModule(
            name="app.auth",
            file_path="app/auth.py",
            classes=[ExtractedClass(name="AuthService")],
        )
        mod_user = ExtractedModule(
            name="app.user",
            file_path="app/user.py",
            imports=[
                ExtractedImport(module="app.auth", imported_names=["AuthService"]),
            ],
        )
        sem_results = [
            _sem("app/auth.py", mod_auth),
            _sem("app/user.py", mod_user),
        ]
        sym_builder = SymbolTableBuilder(repository_id="test-regression")
        symbol_table = sym_builder.build_from_results(sem_results)
        resolver = ImportResolver(repository_id="test-regression")
        result = resolver.resolve_results(sem_results, symbol_table)

        auth_resolutions = [
            result.resolutions[rec.id]
            for rec in result.imports.values()
            if rec.imported_symbol_name == "AuthService"
        ]
        assert len(auth_resolutions) == 1
        assert auth_resolutions[0].status == ImportResolutionStatus.RESOLVED_INTERNAL
        assert "AuthService" in auth_resolutions[0].target_symbol_fqn

    def test_stdlib_imports_still_classified_correctly(self):
        """Standard library imports still resolve as RESOLVED_STDLIB."""
        mod = ExtractedModule(
            name="app.main",
            file_path="app/main.py",
            imports=[
                ExtractedImport(module="os"),
                ExtractedImport(module="json"),
            ],
        )
        sem_results = [_sem("app/main.py", mod)]
        sym_builder = SymbolTableBuilder(repository_id="test-stdlib")
        symbol_table = sym_builder.build_from_results(sem_results)
        resolver = ImportResolver(repository_id="test-stdlib")
        result = resolver.resolve_results(sem_results, symbol_table)

        assert result.metrics.resolved_stdlib == 2
        assert result.metrics.unresolved_count == 0

    def test_external_imports_still_classified_correctly(self):
        """Third-party imports still resolve as RESOLVED_EXTERNAL."""
        mod = ExtractedModule(
            name="app.main",
            file_path="app/main.py",
            imports=[
                ExtractedImport(module="requests"),
                ExtractedImport(module="pydantic"),
            ],
        )
        sem_results = [_sem("app/main.py", mod)]
        sym_builder = SymbolTableBuilder(repository_id="test-external")
        symbol_table = sym_builder.build_from_results(sem_results)
        resolver = ImportResolver(repository_id="test-external")
        result = resolver.resolve_results(sem_results, symbol_table)

        assert result.metrics.resolved_external == 2
        assert result.metrics.unresolved_count == 0
