"""
tests/test_parser_models.py
----------------------------
Comprehensive unit tests for Phase 3.1 — Parser System Data Models.
"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from models.parser import (
    ParserCapabilities,
    ParserError,
    ParserLanguage,
    ParserMetadata,
    ParserOptions,
    ParserResult,
    ParserStatistics,
    ParserStatus,
    ParserVersion,
    ParserWarning,
)


# ---------------------------------------------------------------------------
# Enums Tests
# ---------------------------------------------------------------------------

def test_parser_status_enum_values():
    expected = {
        "success", "partial_success", "syntax_error", "encoding_error",
        "timeout", "unsupported_language", "skipped", "internal_error"
    }
    assert {s.value for s in ParserStatus} == expected


def test_parser_language_enum_values():
    expected = {"python", "typescript", "javascript", "java", "go", "csharp", "unknown"}
    assert {l.value for l in ParserLanguage} == expected


# ---------------------------------------------------------------------------
# Version & Capabilities Models Tests
# ---------------------------------------------------------------------------

def test_parser_version_defaults_and_validation():
    ver = ParserVersion(semver="1.2.3", abi_version=14)
    assert ver.semver == "1.2.3"
    assert ver.abi_version == 14
    assert ver.grammar_version is None

    with pytest.raises(ValidationError):
        ParserVersion(semver="")

    with pytest.raises(ValidationError):
        ParserVersion(semver="1.0.0", abi_version=0)


def test_parser_capabilities_defaults():
    caps = ParserCapabilities()
    assert caps.supports_ast is True
    assert caps.supports_cst is False
    assert caps.supports_symbol_extraction is True
    assert caps.supports_import_extraction is True
    assert caps.supports_error_recovery is True


# ---------------------------------------------------------------------------
# Options Model Tests
# ---------------------------------------------------------------------------

def test_parser_options_defaults_and_custom():
    opts = ParserOptions()
    assert opts.max_file_size_kb == 5000
    assert opts.timeout_seconds == 30.0
    assert opts.extract_comments is True
    assert opts.encoding == "utf-8"

    custom_opts = ParserOptions(
        max_file_size_kb=1000,
        timeout_seconds=10.0,
        custom_flags={"strict_mode": True},
    )
    assert custom_opts.max_file_size_kb == 1000
    assert custom_opts.custom_flags["strict_mode"] is True


def test_parser_options_validation_bounds():
    with pytest.raises(ValidationError):
        ParserOptions(max_file_size_kb=0)

    with pytest.raises(ValidationError):
        ParserOptions(timeout_seconds=0.0)


# ---------------------------------------------------------------------------
# Error & Warning Models Tests
# ---------------------------------------------------------------------------

def test_parser_error_model():
    err = ParserError(
        message="Unexpected token ';'",
        line=10,
        column=5,
        snippet="let x = ;",
    )
    assert err.message == "Unexpected token ';'"
    assert err.line == 10
    assert err.column == 5
    assert err.snippet == "let x = ;"
    assert err.severity == "error"


def test_parser_error_blank_message_raises():
    with pytest.raises(ValidationError):
        ParserError(message="   ")


def test_parser_warning_model():
    warn = ParserWarning(message="Deprecated syntax used", line=4, code="W001")
    assert warn.message == "Deprecated syntax used"
    assert warn.line == 4
    assert warn.code == "W001"


# ---------------------------------------------------------------------------
# Statistics & Metadata Models Tests
# ---------------------------------------------------------------------------

def test_parser_statistics_defaults_and_validation():
    stats = ParserStatistics(
        duration_ms=12.5,
        bytes_parsed=2048,
        lines_parsed=50,
        node_count=120,
    )
    assert stats.duration_ms == 12.5
    assert stats.bytes_parsed == 2048
    assert stats.lines_parsed == 50
    assert stats.node_count == 120

    with pytest.raises(ValidationError):
        ParserStatistics(duration_ms=-1.0)


def test_parser_metadata_creation():
    ver = ParserVersion(semver="0.1.0")
    meta = ParserMetadata(
        parser_name="tree-sitter-python",
        language=ParserLanguage.PYTHON,
        version=ver,
    )
    assert meta.parser_name == "tree-sitter-python"
    assert meta.language == ParserLanguage.PYTHON
    assert meta.version.semver == "0.1.0"
    assert meta.parsed_at is not None


# ---------------------------------------------------------------------------
# ParserResult Tests (Root Container & Serialization)
# ---------------------------------------------------------------------------

def test_parser_result_creation_and_defaults():
    meta = ParserMetadata(
        parser_name="tree-sitter-typescript",
        language=ParserLanguage.TYPESCRIPT,
        version=ParserVersion(semver="1.0.0"),
    )
    res = ParserResult(
        job_id="job-123",
        file_path="src/index.ts",
        language=ParserLanguage.TYPESCRIPT,
        metadata=meta,
    )
    assert res.result_id.startswith("prs-")
    assert res.job_id == "job-123"
    assert res.file_path == "src/index.ts"
    assert res.status == ParserStatus.SUCCESS
    assert res.errors == []
    assert res.warnings == []


def test_parser_result_blank_fields_raise():
    meta = ParserMetadata(
        parser_name="tree-sitter-python",
        language=ParserLanguage.PYTHON,
        version=ParserVersion(semver="1.0.0"),
    )
    with pytest.raises(ValidationError):
        ParserResult(job_id="", file_path="app.py", language=ParserLanguage.PYTHON, metadata=meta)

    with pytest.raises(ValidationError):
        ParserResult(job_id="job-1", file_path="   ", language=ParserLanguage.PYTHON, metadata=meta)


def test_parser_result_error_count_sync():
    meta = ParserMetadata(
        parser_name="tree-sitter-python",
        language=ParserLanguage.PYTHON,
        version=ParserVersion(semver="1.0.0"),
    )
    err = ParserError(message="Syntax error")
    res = ParserResult(
        job_id="job-1",
        file_path="app.py",
        language=ParserLanguage.PYTHON,
        errors=[err],
        metadata=meta,
    )
    assert res.statistics.error_count == 1


def test_parser_result_serialization_round_trip():
    meta = ParserMetadata(
        parser_name="tree-sitter-go",
        language=ParserLanguage.GO,
        version=ParserVersion(semver="2.0.0"),
    )
    res = ParserResult(
        job_id="job-go-1",
        file_path="main.go",
        language=ParserLanguage.GO,
        status=ParserStatus.SUCCESS,
        ast_root={"type": "source_file", "children": []},
        metadata=meta,
    )

    # Dump to dict
    data_dict = res.model_dump()
    assert data_dict["job_id"] == "job-go-1"
    assert data_dict["language"] == ParserLanguage.GO

    # Dump to JSON
    json_str = res.model_dump_json()
    parsed_json = json.loads(json_str)
    assert parsed_json["file_path"] == "main.go"

    # Validate back
    restored = ParserResult.model_validate(data_dict)
    assert restored.result_id == res.result_id
    assert restored.job_id == res.job_id
    assert restored.language == res.language
    assert restored.ast_root == {"type": "source_file", "children": []}
