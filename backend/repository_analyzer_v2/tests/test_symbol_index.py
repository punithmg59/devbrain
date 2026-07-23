"""
tests/test_symbol_index.py
---------------------------
Unit tests and concurrency benchmarks for SymbolIndex multi-index lookup engine.
"""

from concurrent.futures import ThreadPoolExecutor
from models.semantic import ExtractedClass, ExtractedFunction, ExtractedModule, ExtractedVariable, VariableScope
from models.symbol import SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.symbol_table.symbol_index import SymbolIndex


class TestSymbolIndex:
    def test_multi_index_lookups(self):
        mod = ExtractedModule(
            name="app.models",
            file_path="app/models.py",
            classes=[
                ExtractedClass(
                    name="User",
                    methods=[ExtractedFunction(name="save")],
                    class_attributes=[ExtractedVariable(name="table_name", scope=VariableScope.CLASS_ATTRIBUTE)],
                )
            ],
            global_variables=[ExtractedVariable(name="DEFAULT_ROLE", scope=VariableScope.GLOBAL)],
        )

        builder = SymbolTableBuilder(repository_id="repo1")
        table = builder.build_from_module(mod)
        index = SymbolIndex(table)

        assert index.total_indexed == len(table)
        assert index.total_files == 1

        # Lookup by FQN
        user_sym = index.get_by_fqn("app.models.User")
        assert user_sym is not None
        assert user_sym.kind == SymbolKind.CLASS

        # Lookup by ID
        user_by_id = index.get_by_id(user_sym.id)
        assert user_by_id == user_sym

        # Lookup by Name
        saves = index.get_by_name("save")
        assert len(saves) == 1
        assert saves[0].fqn == "app.models.User.save"

        # Lookup by Kind
        classes = index.get_by_kind(SymbolKind.CLASS)
        assert len(classes) == 1
        assert classes[0].name == "User"

        # Lookup by File
        file_syms = index.get_by_file("app/models.py")
        assert len(file_syms) == len(table)

        # Lookup by Parent
        children = index.get_by_parent(user_sym.id)
        child_names = [c.name for c in children]
        assert "save" in child_names
        assert "table_name" in child_names

    def test_search_by_name_prefix(self):
        mod = ExtractedModule(
            name="app.util",
            file_path="app/util.py",
            functions=[
                ExtractedFunction(name="parse_json"),
                ExtractedFunction(name="parse_xml"),
                ExtractedFunction(name="format_date"),
            ],
        )

        builder = SymbolTableBuilder(repository_id="repo1")
        table = builder.build_from_module(mod)
        index = SymbolIndex(table)

        parses = index.search_by_name_prefix("parse")
        names = [p.name for p in parses]
        assert "parse_json" in names
        assert "parse_xml" in names
        assert "format_date" not in names

    def test_concurrent_read_performance(self):
        mod = ExtractedModule(
            name="app.core",
            file_path="app/core.py",
            classes=[
                ExtractedClass(
                    name=f"Service{i}",
                    methods=[ExtractedFunction(name=f"method_{j}") for j in range(10)],
                )
                for i in range(20)
            ],
        )

        builder = SymbolTableBuilder(repository_id="repo1")
        table = builder.build_from_module(mod)
        index = SymbolIndex(table)

        sample_fqn = "app.core.Service5.method_3"

        def read_worker():
            for _ in range(100):
                s = index.get_by_fqn(sample_fqn)
                assert s is not None
                _ = index.get_by_name("method_3")
                _ = index.get_by_kind(SymbolKind.METHOD)

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(read_worker) for _ in range(20)]
            for f in futures:
                f.result()

        latency_us = index.measure_lookup_performance(iterations=1000)
        assert latency_us < 10.0  # Must be fast microsecond-level lookup
