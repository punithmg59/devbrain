"""
tests/test_symbol_validator.py
-------------------------------
Unit tests for SymbolTableValidator integrity validation.
"""

from models.ast import NodeLocation, NodeRange
from models.semantic import ExtractedClass, ExtractedModule
from models.symbol import Symbol, SymbolKind, SymbolLocation
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.symbol_table.symbol_validator import SymbolTableValidator


def make_range(start_line: int, end_line: int) -> NodeRange:
    return NodeRange(
        start=NodeLocation(line=start_line, column=0),
        end=NodeLocation(line=end_line, column=10),
        start_byte=0,
        end_byte=100,
    )


class TestSymbolTableValidator:
    def test_clean_symbol_table_is_valid(self):
        mod = ExtractedModule(
            name="app.valid",
            file_path="app/valid.py",
            classes=[ExtractedClass(name="CleanClass")],
        )

        builder = SymbolTableBuilder(repository_id="repo1")
        table = builder.build_from_module(mod)

        validator = SymbolTableValidator()
        report = validator.validate(table)

        assert report.is_valid is True
        assert report.error_count == 0

    def test_detect_dangling_parent(self):
        table = SymbolTable()
        sym = Symbol(
            id="s-child",
            fqn="app.Orphan",
            name="Orphan",
            kind=SymbolKind.CLASS,
            parent_id="non-existent-parent-id",
            file_path="app.py",
        )
        table.add_symbol(sym)

        validator = SymbolTableValidator()
        report = validator.validate(table)

        assert report.is_valid is False
        assert report.error_count == 1
        issue = report.issues[0]
        assert issue.code == "DANGLING_PARENT"

    def test_detect_duplicate_fqn_warning(self):
        table = SymbolTable()
        sym1 = Symbol(
            id="s-1",
            fqn="app.User",
            name="User",
            kind=SymbolKind.CLASS,
            file_path="app/v1.py",
        )
        sym2 = Symbol(
            id="s-2",
            fqn="app.User",
            name="User",
            kind=SymbolKind.CLASS,
            file_path="app/v2.py",
        )
        table.add_symbol(sym1)
        table.add_symbol(sym2)

        validator = SymbolTableValidator()
        report = validator.validate(table)

        assert report.warning_count >= 1
        codes = [i.code for i in report.issues]
        assert "DUPLICATE_FQN" in codes

    def test_detect_circular_parent(self):
        table = SymbolTable()
        sym1 = Symbol(
            id="s-1",
            fqn="app.A",
            name="A",
            kind=SymbolKind.CLASS,
            parent_id="s-2",
            file_path="app.py",
        )
        sym2 = Symbol(
            id="s-2",
            fqn="app.B",
            name="B",
            kind=SymbolKind.CLASS,
            parent_id="s-1",
            file_path="app.py",
        )
        table.add_symbol(sym1)
        table.add_symbol(sym2)

        validator = SymbolTableValidator()
        report = validator.validate(table)

        assert report.is_valid is False
        codes = [i.code for i in report.issues]
        assert "CIRCULAR_PARENT" in codes

    def test_detect_invalid_location_range(self):
        table = SymbolTable()
        inv_range = NodeRange.model_construct(
            start=NodeLocation(line=20, column=0),
            end=NodeLocation(line=5, column=0),
            start_byte=200,
            end_byte=50,
        )
        inv_loc = SymbolLocation.model_construct(file_path="app.py", range=inv_range)
        sym = Symbol(
            id="s-inv",
            fqn="app.Invalid",
            name="Invalid",
            kind=SymbolKind.CLASS,
            file_path="app.py",
            location=inv_loc,
        )
        table.add_symbol(sym)

        validator = SymbolTableValidator()
        report = validator.validate(table)

        codes = [i.code for i in report.issues]
        assert "INVALID_LOCATION" in codes
