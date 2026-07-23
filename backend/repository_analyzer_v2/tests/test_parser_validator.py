"""
tests/test_parser_validator.py
-------------------------------
Phase 3.10 — Unit and Integration Test Suite for Parser Validation Framework.

Tests all sub-validators (Version, Capabilities, Language, Metadata, Diagnostics, AST,
ParserResult, Requirements) and the unified `ParserValidator` coordinator across valid,
invalid, edge-case, and concurrent workloads.
"""

import pytest
import asyncio
from datetime import datetime, timezone

from models.ast import ASTNode, ASTRoot, NodeLocation, NodeMetadata, NodeRange, NodeRelationship, NodeType
from models.diagnostics import Diagnostic, DiagnosticCode, DiagnosticCollection, DiagnosticSeverity, Suggestion
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
from models.validation import (
    ValidationErrorItem,
    ValidationIssueCode,
    ValidationReport,
    ValidationRequirements,
    ValidationWarningItem,
)
from core.parser_validator import (
    ASTValidator,
    CapabilitiesValidator,
    DiagnosticsValidator,
    LanguageValidator,
    MetadataValidator,
    ParserResultValidator,
    ParserValidator,
    RequirementsValidator,
    VersionValidator,
)
from utils.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_version() -> ParserVersion:
    return ParserVersion(semver="1.2.3", grammar_version="abc1234", abi_version=14)


@pytest.fixture
def valid_capabilities() -> ParserCapabilities:
    return ParserCapabilities(
        supports_ast=True,
        supports_cst=False,
        supports_incremental=False,
        supports_symbol_extraction=True,
    )


@pytest.fixture
def valid_metadata(valid_version: ParserVersion, valid_capabilities: ParserCapabilities) -> ParserMetadata:
    return ParserMetadata(
        parser_name="tree-sitter-python",
        language=ParserLanguage.PYTHON,
        version=valid_version,
        capabilities=valid_capabilities,
        file_hash="a"*64,
    )


@pytest.fixture
def valid_ast_tree() -> ASTRoot:
    root_node = ASTNode(
        node_id="ast-root-1",
        type=NodeType.MODULE,
        name="module",
        range=NodeRange(
            start=NodeLocation(line=1, column=0),
            end=NodeLocation(line=10, column=20),
        ),
    )
    child_node = ASTNode(
        node_id="ast-func-1",
        type=NodeType.FUNCTION,
        name="main",
        range=NodeRange(
            start=NodeLocation(line=2, column=4),
            end=NodeLocation(line=5, column=10),
        ),
    )
    root_node.add_child(child_node)

    root = ASTRoot(
        root_id="tree-1",
        file_path="src/main.py",
        language="python",
        root_node=root_node,
        total_nodes=2,
        max_depth=2,
    )
    return root


@pytest.fixture
def valid_parser_result(valid_metadata: ParserMetadata, valid_ast_tree: ASTRoot) -> ParserResult:
    return ParserResult(
        result_id="prs-123456",
        job_id="job-999",
        file_path="src/main.py",
        language=ParserLanguage.PYTHON,
        status=ParserStatus.SUCCESS,
        errors=[],
        warnings=[],
        statistics=ParserStatistics(
            duration_ms=12.5,
            bytes_parsed=1500,
            lines_parsed=100,
            node_count=2,
            error_count=0,
            warning_count=0,
        ),
        metadata=valid_metadata,
        ast_root=valid_ast_tree.model_dump(),
    )


# ---------------------------------------------------------------------------
# VersionValidator Tests
# ---------------------------------------------------------------------------

class TestVersionValidator:
    def test_valid_semver(self, valid_version: ParserVersion):
        errs, warns = VersionValidator.validate(valid_version)
        assert len(errs) == 0

    def test_invalid_semver_string(self):
        v = ParserVersion.model_construct(semver="v1.2.beta", abi_version=1)
        errs, warns = VersionValidator.validate(v)
        assert len(errs) == 1
        assert errs[0].code == ValidationIssueCode.VERSION_INVALID_SEMVER

    def test_invalid_abi_version(self):
        v = ParserVersion.model_construct(semver="1.0.0", abi_version=0)
        errs, warns = VersionValidator.validate(v)
        assert len(errs) == 1
        assert errs[0].code == ValidationIssueCode.VERSION_INVALID_ABI


# ---------------------------------------------------------------------------
# CapabilitiesValidator Tests
# ---------------------------------------------------------------------------

class TestCapabilitiesValidator:
    def test_valid_capabilities(self, valid_capabilities: ParserCapabilities):
        errs, warns = CapabilitiesValidator.validate(valid_capabilities)
        assert len(errs) == 0

    def test_inconsistent_incremental_without_ast(self):
        caps = ParserCapabilities(supports_ast=False, supports_incremental=True)
        errs, warns = CapabilitiesValidator.validate(caps)
        assert len(warns) == 1
        assert warns[0].code == ValidationIssueCode.CAPABILITIES_INCONSISTENT


# ---------------------------------------------------------------------------
# LanguageValidator Tests
# ---------------------------------------------------------------------------

class TestLanguageValidator:
    def test_valid_language_and_matching_extension(self):
        errs, warns = LanguageValidator.validate(ParserLanguage.PYTHON, file_path="app/server.py")
        assert len(errs) == 0
        assert len(warns) == 0

    def test_mismatched_file_extension_warning(self):
        errs, warns = LanguageValidator.validate(ParserLanguage.PYTHON, file_path="app/server.ts")
        assert len(errs) == 0
        assert len(warns) == 1
        assert warns[0].code == ValidationIssueCode.LANGUAGE_MISMATCH

    def test_unknown_language_warning(self):
        errs, warns = LanguageValidator.validate(ParserLanguage.UNKNOWN)
        assert len(warns) == 1
        assert warns[0].code == ValidationIssueCode.LANGUAGE_UNSUPPORTED


# ---------------------------------------------------------------------------
# MetadataValidator Tests
# ---------------------------------------------------------------------------

class TestMetadataValidator:
    def test_valid_metadata(self, valid_metadata: ParserMetadata):
        errs, warns = MetadataValidator.validate(valid_metadata)
        assert len(errs) == 0

    def test_blank_parser_name(self, valid_version: ParserVersion, valid_capabilities: ParserCapabilities):
        meta = ParserMetadata.model_construct(
            parser_name="   ",
            language=ParserLanguage.PYTHON,
            version=valid_version,
            capabilities=valid_capabilities,
        )
        errs, warns = MetadataValidator.validate(meta)
        assert len(errs) == 1
        assert errs[0].code == ValidationIssueCode.METADATA_INVALID_PARSER_NAME

    def test_invalid_hash_format(self, valid_version: ParserVersion, valid_capabilities: ParserCapabilities):
        meta = ParserMetadata(
            parser_name="tree-sitter",
            language=ParserLanguage.PYTHON,
            version=valid_version,
            capabilities=valid_capabilities,
            file_hash="not_a_hex_hash!",
        )
        errs, warns = MetadataValidator.validate(meta)
        assert len(warns) == 1
        assert warns[0].code == ValidationIssueCode.METADATA_INVALID_HASH


# ---------------------------------------------------------------------------
# DiagnosticsValidator Tests
# ---------------------------------------------------------------------------

class TestDiagnosticsValidator:
    def test_valid_diagnostic_collection(self):
        diag = Diagnostic(
            severity=DiagnosticSeverity.SYNTAX_ERROR,
            code=DiagnosticCode.SYNTAX_UNEXPECTED_TOKEN,
            message="Unexpected token ';'",
            file_path="src/main.py",
            range=NodeRange(
                start=NodeLocation(line=5, column=10),
                end=NodeLocation(line=5, column=11),
            ),
            suggestions=[
                Suggestion(
                    description="Remove trailing semicolon",
                    replacement_text="",
                )
            ],
        )
        col = DiagnosticCollection(file_path="src/main.py", diagnostics=[diag])
        errs, warns = DiagnosticsValidator.validate_collection(col)
        assert len(errs) == 0

    def test_blank_diagnostic_message(self):
        diag = Diagnostic.model_construct(
            severity=DiagnosticSeverity.SYNTAX_ERROR,
            message="   ",
            file_path="src/main.py",
            suggestions=[],
        )
        errs, warns = DiagnosticsValidator.validate_diagnostic(diag)
        assert len(errs) == 1
        assert errs[0].code == ValidationIssueCode.DIAGNOSTIC_BLANK_MESSAGE


# ---------------------------------------------------------------------------
# ASTValidator Tests
# ---------------------------------------------------------------------------

class TestASTValidator:
    def test_valid_ast_root(self, valid_ast_tree: ASTRoot):
        errs, warns = ASTValidator.validate_root(valid_ast_tree)
        assert len(errs) == 0

    def test_ast_coordinate_ordering_error(self):
        bad_range = NodeRange.model_construct(
            start=NodeLocation(line=10, column=5),
            end=NodeLocation(line=5, column=0),
        )
        bad_node = ASTNode.model_construct(
            node_id="bad-1",
            type=NodeType.FUNCTION,
            range=bad_range,
        )
        tree = ASTRoot(
            root_id="tree-bad",
            file_path="src/test.py",
            language="python",
            root_node=bad_node,
        )
        errs, warns = ASTValidator.validate_root(tree)
        assert len(errs) > 0
        assert any(e.code == ValidationIssueCode.AST_RANGE_ORDERING for e in errs)


    def test_ast_parent_child_pointer_mismatch(self):
        parent = ASTNode(
            node_id="p-1",
            type=NodeType.CLASS,
            range=NodeRange(
                start=NodeLocation(line=1, column=0),
                end=NodeLocation(line=20, column=0),
            ),
        )
        child = ASTNode(
            node_id="c-1",
            type=NodeType.METHOD,
            range=NodeRange(
                start=NodeLocation(line=2, column=4),
                end=NodeLocation(line=5, column=4),
            ),
            relationships=NodeRelationship(parent_id="wrong-parent-id"),
        )
        parent.children.append(child)

        tree = ASTRoot(
            root_id="tree-mismatch",
            file_path="src/test.py",
            language="python",
            root_node=parent,
        )

        errs, warns = ASTValidator.validate_root(tree, strict_parent_links=True)
        assert len(errs) == 1
        assert errs[0].code == ValidationIssueCode.AST_PARENT_CHILD_MISMATCH

    def test_ast_duplicate_node_id_or_cycle(self):
        parent = ASTNode(
            node_id="dup-id",
            type=NodeType.MODULE,
            range=NodeRange(
                start=NodeLocation(line=1, column=0),
                end=NodeLocation(line=10, column=0),
            ),
        )
        child = ASTNode(
            node_id="dup-id",  # Duplicate ID
            type=NodeType.STATEMENT,
            range=NodeRange(
                start=NodeLocation(line=2, column=0),
                end=NodeLocation(line=3, column=0),
            ),
            relationships=NodeRelationship(parent_id="dup-id"),
        )
        parent.children.append(child)

        tree = ASTRoot(
            root_id="tree-dup",
            file_path="src/test.py",
            language="python",
            root_node=parent,
        )
        errs, warns = ASTValidator.validate_root(tree)
        assert len(errs) == 1
        assert errs[0].code == ValidationIssueCode.AST_DUPLICATE_NODE_ID


# ---------------------------------------------------------------------------
# ParserResultValidator & RequirementsValidator Tests
# ---------------------------------------------------------------------------

class TestParserResultValidator:
    def test_valid_parser_result(self, valid_parser_result: ParserResult):
        errs, warns = ParserResultValidator.validate(valid_parser_result)
        assert len(errs) == 0

    def test_syntax_error_status_with_empty_errors_list(self, valid_parser_result: ParserResult):
        valid_parser_result.status = ParserStatus.SYNTAX_ERROR
        valid_parser_result.errors = []

        errs, warns = ParserResultValidator.validate(valid_parser_result)
        assert len(errs) == 1
        assert errs[0].code == ValidationIssueCode.STATUS_ERROR_MISMATCH

    def test_requirements_max_duration_exceeded(self, valid_parser_result: ParserResult):
        reqs = ValidationRequirements(max_duration_ms=5.0)  # Actual is 12.5ms
        errs, warns = RequirementsValidator.validate(valid_parser_result, reqs)
        assert len(errs) == 1
        assert errs[0].code == ValidationIssueCode.PARSE_TIMEOUT_EXCEEDED

    def test_requirements_allowed_languages_whitelist(self, valid_parser_result: ParserResult):
        reqs = ValidationRequirements(allowed_languages=["typescript", "java"])
        errs, warns = RequirementsValidator.validate(valid_parser_result, reqs)
        assert len(errs) == 1
        assert errs[0].code == ValidationIssueCode.LANGUAGE_UNSUPPORTED

    def test_requirements_min_semver(self, valid_parser_result: ParserResult):
        reqs = ValidationRequirements(min_semver="2.0.0")  # Actual is 1.2.3
        errs, warns = RequirementsValidator.validate(valid_parser_result, reqs)
        assert len(errs) == 1
        assert errs[0].code == ValidationIssueCode.REQUIREMENT_FAILED


# ---------------------------------------------------------------------------
# ParserValidator Facade & Integration Tests
# ---------------------------------------------------------------------------

class TestParserValidatorFacade:
    def test_validate_result_success(self, valid_parser_result: ParserResult):
        validator = ParserValidator()
        report = validator.validate_result(valid_parser_result)

        assert report.is_valid is True
        assert report.has_errors is False
        assert report.error_count == 0
        assert report.duration_ms >= 0.0

    def test_raise_if_invalid_throws_domain_validation_error(self, valid_parser_result: ParserResult):
        valid_parser_result.status = ParserStatus.SYNTAX_ERROR
        valid_parser_result.errors = []

        validator = ParserValidator()
        report = validator.validate_result(valid_parser_result)

        assert report.is_valid is False
        with pytest.raises(ValidationError) as exc_info:
            report.raise_if_invalid(stage_name="TestStage")

        assert "Parser validation failed" in str(exc_info.value)
        assert exc_info.value.stage_name == "TestStage"

    @pytest.mark.asyncio
    async def test_async_validation_methods(self, valid_parser_result: ParserResult, valid_ast_tree: ASTRoot):
        validator = ParserValidator()

        res_report = await validator.validate_result_async(valid_parser_result)
        assert res_report.is_valid is True

        ast_report = await validator.validate_ast_async(valid_ast_tree)
        assert ast_report.is_valid is True

    def test_sub_validation_facade_delegation(self, valid_metadata: ParserMetadata, valid_capabilities: ParserCapabilities, valid_version: ParserVersion):
        validator = ParserValidator()

        meta_rep = validator.validate_metadata(valid_metadata)
        assert meta_rep.is_valid is True

        cap_rep = validator.validate_capabilities(valid_capabilities)
        assert cap_rep.is_valid is True

        ver_rep = validator.validate_version(valid_version)
        assert ver_rep.is_valid is True

        lang_rep = validator.validate_language(ParserLanguage.PYTHON, file_path="main.py")
        assert lang_rep.is_valid is True
