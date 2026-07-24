"""
tests/test_re_export_builder.py
--------------------------------
Unit tests for ReExportBuilder — scanning __init__.py ExtractedModule objects
and producing ExportRecord instances for all supported re-export patterns.
"""

from models.semantic import (
    ExtractedImport,
    ExtractedModule,
    ExtractedVariable,
    SemanticExtractionResult,
    VariableScope,
)
from models.re_export_models import ExportType
from analysis.re_export_resolution.re_export_builder import ReExportBuilder
from analysis.import_resolution.module_index import ModuleIndex


def _make_sem_result(file_path: str, module: ExtractedModule) -> SemanticExtractionResult:
    return SemanticExtractionResult(file_path=file_path, language="python", module=module)


def _make_module_index(*pairs) -> ModuleIndex:
    """pairs: (file_path, fqn)"""
    idx = ModuleIndex()
    for fp, fqn in pairs:
        idx.register_file(fp, fqn)
    return idx


class TestReExportBuilderIsInitFile:
    def test_init_file_detected(self):
        assert ReExportBuilder._is_init_file("fastapi/__init__.py")
        assert ReExportBuilder._is_init_file("app/auth/__init__.py")
        assert ReExportBuilder._is_init_file("__init__.py")

    def test_non_init_file_rejected(self):
        assert not ReExportBuilder._is_init_file("fastapi/applications.py")
        assert not ReExportBuilder._is_init_file("app/main.py")


class TestReExportBuilderFromImport:
    def test_simple_relative_from_import(self):
        """from .applications import FastAPI → ExportRecord(exported_name='FastAPI')"""
        mod = ExtractedModule(
            name="fastapi",
            file_path="fastapi/__init__.py",
            imports=[
                ExtractedImport(
                    module="applications",
                    imported_names=["FastAPI"],
                    is_relative=True,
                    relative_level=1,
                )
            ],
        )
        builder = ReExportBuilder()
        module_index = _make_module_index(("fastapi/__init__.py", "fastapi"))
        records = builder.build_from_results(
            [_make_sem_result("fastapi/__init__.py", mod)],
            module_index,
        )

        assert len(records) == 1
        rec = records[0]
        assert rec.exported_name == "FastAPI"
        assert rec.original_name == "FastAPI"
        assert rec.package_fqn == "fastapi"
        assert rec.source_module_fqn == "fastapi.applications"
        assert rec.export_type == ExportType.FROM_IMPORT
        assert rec.alias is None
        assert not rec.is_star_export

    def test_multiple_names_from_same_module(self):
        """from .routing import APIRouter, Include"""
        mod = ExtractedModule(
            name="fastapi",
            file_path="fastapi/__init__.py",
            imports=[
                ExtractedImport(
                    module="routing",
                    imported_names=["APIRouter", "Include"],
                    is_relative=True,
                    relative_level=1,
                )
            ],
        )
        builder = ReExportBuilder()
        module_index = _make_module_index(("fastapi/__init__.py", "fastapi"))
        records = builder.build_from_results(
            [_make_sem_result("fastapi/__init__.py", mod)], module_index
        )

        assert len(records) == 2
        names = {r.exported_name for r in records}
        assert names == {"APIRouter", "Include"}
        for r in records:
            assert r.source_module_fqn == "fastapi.routing"


class TestReExportBuilderAlias:
    def test_aliased_from_import(self):
        """from .routing import APIRouter as Router"""
        mod = ExtractedModule(
            name="mylib",
            file_path="mylib/__init__.py",
            imports=[
                ExtractedImport(
                    module="routing",
                    imported_names=["APIRouter"],
                    aliases={"APIRouter": "Router"},
                    is_relative=True,
                    relative_level=1,
                )
            ],
        )
        builder = ReExportBuilder()
        module_index = _make_module_index(("mylib/__init__.py", "mylib"))
        records = builder.build_from_results(
            [_make_sem_result("mylib/__init__.py", mod)], module_index
        )

        assert len(records) == 1
        rec = records[0]
        assert rec.exported_name == "Router"
        assert rec.original_name == "APIRouter"
        assert rec.alias == "Router"
        assert rec.export_type == ExportType.FROM_IMPORT_ALIAS


class TestReExportBuilderStarExport:
    def test_star_export(self):
        """from .utils import *"""
        mod = ExtractedModule(
            name="mylib",
            file_path="mylib/__init__.py",
            imports=[
                ExtractedImport(
                    module="utils",
                    imported_names=["*"],
                    is_relative=True,
                    relative_level=1,
                )
            ],
        )
        builder = ReExportBuilder()
        module_index = _make_module_index(("mylib/__init__.py", "mylib"))
        records = builder.build_from_results(
            [_make_sem_result("mylib/__init__.py", mod)], module_index
        )

        assert len(records) == 1
        rec = records[0]
        assert rec.is_star_export
        assert rec.exported_name == "*"
        assert rec.source_module_fqn == "mylib.utils"
        assert rec.export_type == ExportType.STAR_EXPORT


class TestReExportBuilderAllList:
    def test_all_list_declaration(self):
        """__all__ = ["FastAPI", "APIRouter"]"""
        mod = ExtractedModule(
            name="fastapi",
            file_path="fastapi/__init__.py",
            global_variables=[
                ExtractedVariable(
                    name="__all__",
                    scope=VariableScope.GLOBAL,
                    value_snippet='["FastAPI", "APIRouter"]',
                )
            ],
        )
        builder = ReExportBuilder()
        module_index = _make_module_index(("fastapi/__init__.py", "fastapi"))
        records = builder.build_from_results(
            [_make_sem_result("fastapi/__init__.py", mod)], module_index
        )

        assert len(records) == 2
        names = {r.exported_name for r in records}
        assert names == {"FastAPI", "APIRouter"}
        for r in records:
            assert r.export_type == ExportType.ALL_LIST
            assert r.source_module_fqn is None

    def test_all_augmented_assign(self):
        """__all__ += ["ExtraClass"]"""
        mod = ExtractedModule(
            name="mylib",
            file_path="mylib/__init__.py",
            global_variables=[
                ExtractedVariable(
                    name="__all__",
                    scope=VariableScope.GLOBAL,
                    value_snippet='__all__ += ["ExtraClass"]',
                )
            ],
        )
        builder = ReExportBuilder()
        module_index = _make_module_index(("mylib/__init__.py", "mylib"))
        records = builder.build_from_results(
            [_make_sem_result("mylib/__init__.py", mod)], module_index
        )

        assert len(records) == 1
        assert records[0].exported_name == "ExtraClass"
        assert records[0].export_type == ExportType.ALL_AUGMENTED


class TestReExportBuilderNonInitFilesIgnored:
    def test_non_init_file_skipped(self):
        """Regular .py files should produce zero export records."""
        mod = ExtractedModule(
            name="fastapi.applications",
            file_path="fastapi/applications.py",
            imports=[
                ExtractedImport(module="os", imported_names=["path"]),
            ],
        )
        builder = ReExportBuilder()
        module_index = _make_module_index(("fastapi/applications.py", "fastapi.applications"))
        records = builder.build_from_results(
            [_make_sem_result("fastapi/applications.py", mod)], module_index
        )
        assert len(records) == 0
