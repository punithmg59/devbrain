"""
tests/test_diagnostics.py
--------------------------
Comprehensive unit tests for Phase 3.3 — Parser Diagnostics System.
"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from models.ast import NodeLocation, NodeRange
from models.diagnostics import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticCollection,
    DiagnosticSeverity,
    Suggestion,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_range(line: int = 5, column: int = 10) -> NodeRange:
    return NodeRange(
        start=NodeLocation(line=line, column=column),
        end=NodeLocation(line=line, column=column + 5),
    )


# ---------------------------------------------------------------------------
# Enums Tests
# ---------------------------------------------------------------------------

def test_diagnostic_severity_enum():
    expected = {"hint", "warning", "syntax_error", "recoverable_error", "fatal_error"}
    assert {s.value for s in DiagnosticSeverity} == expected


def test_diagnostic_code_enum():
    assert DiagnosticCode.SYNTAX_UNEXPECTED_TOKEN.value == "SYNTAX_001"
    assert DiagnosticCode.FATAL_PARSE_TIMEOUT.value == "FATAL_001"


# ---------------------------------------------------------------------------
# Suggestion Tests
# ---------------------------------------------------------------------------

def test_suggestion_model():
    sug = Suggestion(
        description="Insert missing semicolon",
        replacement_text=";",
        range=make_range(2, 15),
    )
    assert sug.suggestion_id.startswith("sug-")
    assert sug.description == "Insert missing semicolon"
    assert sug.replacement_text == ";"
    assert sug.range is not None


def test_suggestion_blank_description_raises():
    with pytest.raises(ValidationError):
        Suggestion(description="   ")


# ---------------------------------------------------------------------------
# Diagnostic Tests
# ---------------------------------------------------------------------------

def test_diagnostic_model_creation():
    diag = Diagnostic(
        severity=DiagnosticSeverity.SYNTAX_ERROR,
        code=DiagnosticCode.SYNTAX_UNEXPECTED_TOKEN,
        message="Unexpected token '}'",
        file_path="src/parser.py",
        range=make_range(12, 4),
        is_recoverable=True,
        tags=["syntax"],
    )
    assert diag.diagnostic_id.startswith("diag-")
    assert diag.severity == DiagnosticSeverity.SYNTAX_ERROR
    assert diag.code == DiagnosticCode.SYNTAX_UNEXPECTED_TOKEN
    assert diag.message == "Unexpected token '}'"
    assert diag.file_path == "src/parser.py"
    assert diag.is_recoverable is True


def test_diagnostic_blank_strings_raise():
    with pytest.raises(ValidationError):
        Diagnostic(
            severity=DiagnosticSeverity.WARNING,
            message="   ",
            file_path="app.py",
        )

    with pytest.raises(ValidationError):
        Diagnostic(
            severity=DiagnosticSeverity.WARNING,
            message="Valid message",
            file_path="",
        )


# ---------------------------------------------------------------------------
# DiagnosticCollection Tests
# ---------------------------------------------------------------------------

def test_diagnostic_collection_operations():
    col = DiagnosticCollection(file_path="src/main.py")
    assert col.collection_id.startswith("dcol-")
    assert col.file_path == "src/main.py"
    assert not col.has_errors
    assert not col.has_warnings

    # Add warning
    w = col.add_warning("Unused variable 'x'", code="W001")
    assert col.has_warnings
    assert not col.has_errors
    assert w.severity == DiagnosticSeverity.WARNING

    # Add recoverable syntax error
    e1 = col.add_error("Missing closing parenthesis", is_fatal=False)
    assert col.has_errors
    assert not col.has_fatal_errors
    assert e1.is_recoverable is True

    # Add fatal error
    e2 = col.add_error("Parse timeout exceeded", code=DiagnosticCode.FATAL_PARSE_TIMEOUT, is_fatal=True)
    assert col.has_fatal_errors
    assert e2.is_recoverable is False


def test_diagnostic_collection_filtering():
    col = DiagnosticCollection(file_path="src/utils.py")
    col.add_warning("Warn 1")
    col.add_warning("Warn 2")
    col.add_error("Error 1", is_fatal=False)

    warnings = col.get_by_severity(DiagnosticSeverity.WARNING)
    assert len(warnings) == 2

    errors = col.get_by_severity(DiagnosticSeverity.SYNTAX_ERROR)
    assert len(errors) == 1


def test_diagnostic_collection_serialization_round_trip():
    col = DiagnosticCollection(file_path="src/app.py")
    sug = Suggestion(description="Remove unused import", replacement_text="")
    diag = Diagnostic(
        severity=DiagnosticSeverity.WARNING,
        message="Unused import os",
        file_path="src/app.py",
        suggestions=[sug],
    )
    col.add_diagnostic(diag)

    # JSON serialization
    json_str = col.to_json()
    data = json.loads(json_str)

    assert data["file_path"] == "src/app.py"
    assert len(data["diagnostics"]) == 1
    assert data["diagnostics"][0]["suggestions"][0]["description"] == "Remove unused import"

    # Deserialization
    restored = DiagnosticCollection.model_validate(data)
    assert restored.collection_id == col.collection_id
    assert restored.file_path == col.file_path
    assert len(restored.diagnostics) == 1
    assert restored.diagnostics[0].suggestions[0].description == "Remove unused import"
