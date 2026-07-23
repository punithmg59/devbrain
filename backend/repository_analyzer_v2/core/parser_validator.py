"""
core/parser_validator.py
------------------------
Phase 3.10 — Independent Parser Validation Framework.

Provides production-quality, type-safe, thread-safe, and async-capable validation for:
- ParserResult
- AST (ASTRoot, ASTNode, geometry, ranges, parent-child graph links, metrics, cycle detection)
- Diagnostics (Diagnostic, DiagnosticCollection, codes, severities, ranges, suggestions)
- Metadata (ParserMetadata, hash validation)
- Capabilities (ParserCapabilities)
- Version (ParserVersion, semver validation)
- Language (ParserLanguage, file extension alignment)
- Operational Requirements (ValidationRequirements engine)

Design Principles
-----------------
- **Zero Parser Engine Dependencies**: Independent validation framework operating purely
  on data models without executing Tree-sitter or external parsers.
- **SOLID Architecture**: Clean separation into specialized sub-validators coordinated by
  the unified `ParserValidator` facade.
- **Thread-Safe & Async-First**: Stateless validation execution safe for multi-threaded and
  concurrent async workloads.
- **Structured Logging & Errors**: Integrated with DevBrain logger and `utils.exceptions.ValidationError`.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from models.ast import ASTNode, ASTRoot, NodeLocation, NodeRange
from models.diagnostics import Diagnostic, DiagnosticCollection
from models.parser import (
    ParserCapabilities,
    ParserLanguage,
    ParserMetadata,
    ParserResult,
    ParserStatus,
    ParserVersion,
)
from models.validation import (
    ValidationErrorItem,
    ValidationIssueCode,
    ValidationReport,
    ValidationRequirements,
    ValidationWarningItem,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Regex for Semantic Versioning (SemVer 2.0.0)
SEMVER_REGEX = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

# Common file extensions by ParserLanguage
LANGUAGE_EXTENSIONS: Dict[ParserLanguage, Set[str]] = {
    ParserLanguage.PYTHON: {".py", ".pyi", ".pyx"},
    ParserLanguage.TYPESCRIPT: {".ts", ".tsx", ".mts", ".cts"},
    ParserLanguage.JAVASCRIPT: {".js", ".jsx", ".mjs", ".cjs"},
    ParserLanguage.JAVA: {".java"},
    ParserLanguage.GO: {".go"},
    ParserLanguage.CSHARP: {".cs"},
}


class VersionValidator:
    """Validates parser semver format, ABI compatibility version, and grammar version."""

    @staticmethod
    def validate(version: ParserVersion, field_prefix: str = "metadata.version") -> Tuple[List[ValidationErrorItem], List[ValidationWarningItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if not version.semver or not version.semver.strip():
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.VERSION_INVALID_SEMVER,
                    message="Parser semver string must not be empty or blank.",
                    field_path=f"{field_prefix}.semver",
                )
            )
        elif not SEMVER_REGEX.match(version.semver.strip()):
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.VERSION_INVALID_SEMVER,
                    message=f"Parser version '{version.semver}' does not follow Semantic Versioning (X.Y.Z).",
                    field_path=f"{field_prefix}.semver",
                    context={"provided": version.semver},
                )
            )

        if version.abi_version is not None and version.abi_version < 1:
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.VERSION_INVALID_ABI,
                    message=f"ABI version must be >= 1, got {version.abi_version}.",
                    field_path=f"{field_prefix}.abi_version",
                )
            )

        if version.grammar_version is not None and not version.grammar_version.strip():
            warnings.append(
                ValidationWarningItem(
                    code=ValidationIssueCode.VERSION_INVALID_SEMVER,
                    message="Grammar version string is specified but empty or whitespace.",
                    field_path=f"{field_prefix}.grammar_version",
                )
            )

        return errors, warnings


class CapabilitiesValidator:
    """Validates parser capability configurations."""

    @staticmethod
    def validate(capabilities: ParserCapabilities, field_prefix: str = "metadata.capabilities") -> Tuple[List[ValidationErrorItem], List[ValidationWarningItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        # Sanity check: If incremental is supported but AST is not supported
        if capabilities.supports_incremental and not capabilities.supports_ast:
            warnings.append(
                ValidationWarningItem(
                    code=ValidationIssueCode.CAPABILITIES_INCONSISTENT,
                    message="Parser declares supports_incremental=True but supports_ast=False.",
                    field_path=f"{field_prefix}.supports_incremental",
                )
            )

        return errors, warnings


class LanguageValidator:
    """Validates target programming language specifications and file path extension alignment."""

    @staticmethod
    def validate(
        language: ParserLanguage,
        file_path: Optional[str] = None,
        field_prefix: str = "language",
    ) -> Tuple[List[ValidationErrorItem], List[ValidationWarningItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if not isinstance(language, ParserLanguage):
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.LANGUAGE_UNSUPPORTED,
                    message=f"Invalid language type: expected ParserLanguage enum, got {type(language).__name__}.",
                    field_path=field_prefix,
                )
            )
            return errors, warnings

        if language == ParserLanguage.UNKNOWN:
            warnings.append(
                ValidationWarningItem(
                    code=ValidationIssueCode.LANGUAGE_UNSUPPORTED,
                    message="Language is specified as UNKNOWN.",
                    field_path=field_prefix,
                )
            )

        if file_path and language in LANGUAGE_EXTENSIONS:
            allowed_exts = LANGUAGE_EXTENSIONS[language]
            matched = any(file_path.lower().endswith(ext) for ext in allowed_exts)
            if not matched:
                warnings.append(
                    ValidationWarningItem(
                        code=ValidationIssueCode.LANGUAGE_MISMATCH,
                        message=f"File path '{file_path}' extension does not match expected extensions for {language.value} ({', '.join(sorted(allowed_exts))}).",
                        field_path="file_path",
                        context={"file_path": file_path, "language": language.value},
                    )
                )

        return errors, warnings


class MetadataValidator:
    """Validates parser engine metadata, parser name, version, capabilities, and file hashes."""

    @staticmethod
    def validate(metadata: ParserMetadata, field_prefix: str = "metadata") -> Tuple[List[ValidationErrorItem], List[ValidationWarningItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if not metadata.parser_name or not metadata.parser_name.strip():
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.METADATA_INVALID_PARSER_NAME,
                    message="Parser name in metadata must not be blank.",
                    field_path=f"{field_prefix}.parser_name",
                )
            )

        # Validate nested language, version, capabilities
        lang_errs, lang_warns = LanguageValidator.validate(metadata.language, field_prefix=f"{field_prefix}.language")
        ver_errs, ver_warns = VersionValidator.validate(metadata.version, field_prefix=f"{field_prefix}.version")
        cap_errs, cap_warns = CapabilitiesValidator.validate(metadata.capabilities, field_prefix=f"{field_prefix}.capabilities")

        errors.extend(lang_errs + ver_errs + cap_errs)
        warnings.extend(lang_warns + ver_warns + cap_warns)

        if metadata.file_hash is not None:
            clean_hash = metadata.file_hash.strip()
            if not clean_hash:
                warnings.append(
                    ValidationWarningItem(
                        code=ValidationIssueCode.METADATA_INVALID_HASH,
                        message="File hash string is specified but empty or whitespace.",
                        field_path=f"{field_prefix}.file_hash",
                    )
                )
            elif len(clean_hash) not in (32, 40, 64) or not all(c in "0123456789abcdefABCDEF" for c in clean_hash):
                warnings.append(
                    ValidationWarningItem(
                        code=ValidationIssueCode.METADATA_INVALID_HASH,
                        message=f"File hash '{clean_hash}' does not match standard hexadecimal hash length (MD5/SHA1/SHA256).",
                        field_path=f"{field_prefix}.file_hash",
                    )
                )

        return errors, warnings


class DiagnosticsValidator:
    """Validates Diagnostic records and DiagnosticCollection instances."""

    @staticmethod
    def validate_diagnostic(
        diag: Diagnostic,
        field_prefix: str = "diagnostic",
    ) -> Tuple[List[ValidationErrorItem], List[ValidationWarningItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if not diag.message or not diag.message.strip():
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.DIAGNOSTIC_BLANK_MESSAGE,
                    message="Diagnostic message must not be blank.",
                    field_path=f"{field_prefix}.message",
                )
            )

        if not diag.file_path or not diag.file_path.strip():
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.INVALID_FILE_PATH,
                    message="Diagnostic file_path must not be blank.",
                    field_path=f"{field_prefix}.file_path",
                )
            )

        if diag.range is not None:
            range_errs = DiagnosticsValidator._validate_node_range(diag.range, field_prefix=f"{field_prefix}.range")
            errors.extend(range_errs)

        for idx, sug in enumerate(diag.suggestions):
            if not sug.description or not sug.description.strip():
                errors.append(
                    ValidationErrorItem(
                        code=ValidationIssueCode.DIAGNOSTIC_SUGGESTION_INVALID,
                        message=f"Suggestion description at index {idx} must not be blank.",
                        field_path=f"{field_prefix}.suggestions[{idx}].description",
                    )
                )
            if sug.range is not None:
                sug_range_errs = DiagnosticsValidator._validate_node_range(sug.range, field_prefix=f"{field_prefix}.suggestions[{idx}].range")
                errors.extend(sug_range_errs)

        return errors, warnings

    @staticmethod
    def validate_collection(
        collection: DiagnosticCollection,
        field_prefix: str = "diagnostics",
    ) -> Tuple[List[ValidationErrorItem], List[ValidationWarningItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if not collection.file_path or not collection.file_path.strip():
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.INVALID_FILE_PATH,
                    message="DiagnosticCollection file_path must not be blank.",
                    field_path=f"{field_prefix}.file_path",
                )
            )

        for idx, diag in enumerate(collection.diagnostics):
            d_errs, d_warns = DiagnosticsValidator.validate_diagnostic(diag, field_prefix=f"{field_prefix}.diagnostics[{idx}]")
            errors.extend(d_errs)
            warnings.extend(d_warns)

        return errors, warnings

    @staticmethod
    def _validate_node_range(range_obj: NodeRange, field_prefix: str) -> List[ValidationErrorItem]:
        errors: List[ValidationErrorItem] = []
        if range_obj.start.line < 1:
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.AST_INVALID_COORDINATES,
                    message=f"Start line must be >= 1, got {range_obj.start.line}.",
                    field_path=f"{field_prefix}.start.line",
                )
            )
        if range_obj.start.column < 0:
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.AST_INVALID_COORDINATES,
                    message=f"Start column must be >= 0, got {range_obj.start.column}.",
                    field_path=f"{field_prefix}.start.column",
                )
            )
        if range_obj.end.line < range_obj.start.line:
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.AST_RANGE_ORDERING,
                    message=f"End line ({range_obj.end.line}) precedes start line ({range_obj.start.line}).",
                    field_path=f"{field_prefix}.end.line",
                )
            )
        elif range_obj.end.line == range_obj.start.line and range_obj.end.column < range_obj.start.column:
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.AST_RANGE_ORDERING,
                    message=f"End column ({range_obj.end.column}) precedes start column ({range_obj.start.column}) on line {range_obj.start.line}.",
                    field_path=f"{field_prefix}.end.column",
                )
            )
        return errors


class ASTValidator:
    """
    Validates ASTRoot and ASTNode structures, coordinates, range ordering,
    parent-child range containment, bidirectional relationship links, metric accuracy,
    and cycle prevention.
    """

    @staticmethod
    def validate_node(
        node: ASTNode,
        parent: Optional[ASTNode] = None,
        visited_ids: Optional[Set[str]] = None,
        field_prefix: str = "node",
        strict_parent_links: bool = True,
        strict_range_containment: bool = True,
    ) -> Tuple[List[ValidationErrorItem], List[ValidationWarningItem], int, int]:
        """
        Recursively validates an ASTNode and its children.

        Returns
        -------
        (errors, warnings, node_count, max_depth)
        """
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if visited_ids is None:
            visited_ids = set()

        # Cycle & duplicate node ID check
        if node.node_id in visited_ids:
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.AST_DUPLICATE_NODE_ID,
                    message=f"Duplicate or cyclic AST node_id encountered: '{node.node_id}'.",
                    field_path=f"{field_prefix}.node_id",
                    context={"node_id": node.node_id},
                )
            )
            return errors, warnings, 1, 1

        visited_ids.add(node.node_id)

        # Coordinate bounds & range ordering
        range_errs = DiagnosticsValidator._validate_node_range(node.range, field_prefix=f"{field_prefix}.range")
        errors.extend(range_errs)

        # Parent-Child relationship check
        if parent is not None:
            if strict_parent_links:
                if node.relationships.parent_id != parent.node_id:
                    errors.append(
                        ValidationErrorItem(
                            code=ValidationIssueCode.AST_PARENT_CHILD_MISMATCH,
                            message=f"Child node '{node.node_id}' parent_id '{node.relationships.parent_id}' does not match actual parent node_id '{parent.node_id}'.",
                            field_path=f"{field_prefix}.relationships.parent_id",
                            context={"child_id": node.node_id, "expected_parent": parent.node_id, "actual_parent": node.relationships.parent_id},
                        )
                    )

            if strict_range_containment:
                # Check if child is strictly inside parent range
                p_start = (parent.range.start.line, parent.range.start.column)
                p_end = (parent.range.end.line, parent.range.end.column)
                c_start = (node.range.start.line, node.range.start.column)
                c_end = (node.range.end.line, node.range.end.column)

                if c_start < p_start or c_end > p_end:
                    warnings.append(
                        ValidationWarningItem(
                            code=ValidationIssueCode.AST_CHILD_RANGE_OUT_OF_BOUNDS,
                            message=f"Child node '{node.node_id}' range [{c_start}..{c_end}] extends outside parent '{parent.node_id}' range [{p_start}..{p_end}].",
                            field_path=f"{field_prefix}.range",
                            context={"child_id": node.node_id, "parent_id": parent.node_id},
                        )
                    )

        total_nodes = 1
        max_child_depth = 0

        for idx, child in enumerate(node.children):
            c_errs, c_warns, c_count, c_depth = ASTValidator.validate_node(
                child,
                parent=node,
                visited_ids=visited_ids,
                field_prefix=f"{field_prefix}.children[{idx}]",
                strict_parent_links=strict_parent_links,
                strict_range_containment=strict_range_containment,
            )
            errors.extend(c_errs)
            warnings.extend(c_warns)
            total_nodes += c_count
            if c_depth > max_child_depth:
                max_child_depth = c_depth

        return errors, warnings, total_nodes, 1 + max_child_depth

    @staticmethod
    def validate_root(
        root: ASTRoot,
        field_prefix: str = "ast_root",
        strict_parent_links: bool = True,
        strict_range_containment: bool = True,
    ) -> Tuple[List[ValidationErrorItem], List[ValidationWarningItem]]:
        """Validates complete ASTRoot container and syntax tree metrics."""
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if not root.file_path or not root.file_path.strip():
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.INVALID_FILE_PATH,
                    message="ASTRoot file_path must not be blank.",
                    field_path=f"{field_prefix}.file_path",
                )
            )

        if not root.language or not root.language.strip():
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.LANGUAGE_UNSUPPORTED,
                    message="ASTRoot language must not be blank.",
                    field_path=f"{field_prefix}.language",
                )
            )

        if root.root_node is None:
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.AST_MISSING_ROOT,
                    message="ASTRoot root_node is missing.",
                    field_path=f"{field_prefix}.root_node",
                )
            )
            return errors, warnings

        # Validate tree starting from root_node
        n_errs, n_warns, calculated_nodes, calculated_depth = ASTValidator.validate_node(
            root.root_node,
            parent=None,
            visited_ids=set(),
            field_prefix=f"{field_prefix}.root_node",
            strict_parent_links=strict_parent_links,
            strict_range_containment=strict_range_containment,
        )
        errors.extend(n_errs)
        warnings.extend(n_warns)

        # Check metrics accuracy
        if root.total_nodes != calculated_nodes:
            warnings.append(
                ValidationWarningItem(
                    code=ValidationIssueCode.AST_METRICS_MISMATCH,
                    message=f"ASTRoot.total_nodes ({root.total_nodes}) does not match calculated total node count ({calculated_nodes}).",
                    field_path=f"{field_prefix}.total_nodes",
                    context={"declared": root.total_nodes, "calculated": calculated_nodes},
                )
            )

        if root.max_depth != calculated_depth:
            warnings.append(
                ValidationWarningItem(
                    code=ValidationIssueCode.AST_METRICS_MISMATCH,
                    message=f"ASTRoot.max_depth ({root.max_depth}) does not match calculated max depth ({calculated_depth}).",
                    field_path=f"{field_prefix}.max_depth",
                    context={"declared": root.max_depth, "calculated": calculated_depth},
                )
            )

        return errors, warnings


class ParserResultValidator:
    """Validates top-level ParserResult objects for status-error consistency and statistics alignment."""

    @staticmethod
    def validate(
        result: ParserResult,
        field_prefix: str = "parser_result",
        strict_parent_links: bool = True,
        strict_range_containment: bool = True,
    ) -> Tuple[List[ValidationErrorItem], List[ValidationWarningItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if not result.result_id or not result.result_id.strip():
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.REQUIRED_FIELD_MISSING,
                    message="ParserResult result_id must not be blank.",
                    field_path=f"{field_prefix}.result_id",
                )
            )

        if not result.job_id or not result.job_id.strip():
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.INVALID_JOB_ID,
                    message="ParserResult job_id must not be blank.",
                    field_path=f"{field_prefix}.job_id",
                )
            )

        if not result.file_path or not result.file_path.strip():
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.INVALID_FILE_PATH,
                    message="ParserResult file_path must not be blank.",
                    field_path=f"{field_prefix}.file_path",
                )
            )

        # Status vs Error consistency
        if result.status == ParserStatus.SYNTAX_ERROR and len(result.errors) == 0:
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.STATUS_ERROR_MISMATCH,
                    message="ParserResult status is SYNTAX_ERROR but errors list is empty.",
                    field_path=f"{field_prefix}.errors",
                )
            )

        if result.status == ParserStatus.SUCCESS and len(result.errors) > 0:
            has_fatal_or_syntax = any(e.severity in ("error", "fatal", "syntax_error") for e in result.errors)
            if has_fatal_or_syntax:
                errors.append(
                    ValidationErrorItem(
                        code=ValidationIssueCode.STATUS_ERROR_MISMATCH,
                        message="ParserResult status is SUCCESS but contains syntax or fatal errors.",
                        field_path=f"{field_prefix}.errors",
                    )
                )

        # Statistics checks
        if result.statistics.error_count != len(result.errors):
            warnings.append(
                ValidationWarningItem(
                    code=ValidationIssueCode.STATISTICS_MISMATCH,
                    message=f"ParserStatistics error_count ({result.statistics.error_count}) does not match errors list length ({len(result.errors)}).",
                    field_path=f"{field_prefix}.statistics.error_count",
                )
            )

        if result.statistics.warning_count != len(result.warnings):
            warnings.append(
                ValidationWarningItem(
                    code=ValidationIssueCode.STATISTICS_MISMATCH,
                    message=f"ParserStatistics warning_count ({result.statistics.warning_count}) does not match warnings list length ({len(result.warnings)}).",
                    field_path=f"{field_prefix}.statistics.warning_count",
                )
            )

        # Metadata validation
        m_errs, m_warns = MetadataValidator.validate(result.metadata, field_prefix=f"{field_prefix}.metadata")
        errors.extend(m_errs)
        warnings.extend(m_warns)

        # AST payload validation (if AST payload or ASTRoot is provided)
        if result.ast_root is not None:
            if isinstance(result.ast_root, ASTRoot):
                ast_errs, ast_warns = ASTValidator.validate_root(
                    result.ast_root,
                    field_prefix=f"{field_prefix}.ast_root",
                    strict_parent_links=strict_parent_links,
                    strict_range_containment=strict_range_containment,
                )
                errors.extend(ast_errs)
                warnings.extend(ast_warns)
            elif isinstance(result.ast_root, dict):
                try:
                    parsed_root = ASTRoot.model_validate(result.ast_root)
                    ast_errs, ast_warns = ASTValidator.validate_root(
                        parsed_root,
                        field_prefix=f"{field_prefix}.ast_root",
                        strict_parent_links=strict_parent_links,
                        strict_range_containment=strict_range_containment,
                    )
                    errors.extend(ast_errs)
                    warnings.extend(ast_warns)
                except Exception as ex:
                    errors.append(
                        ValidationErrorItem(
                            code=ValidationIssueCode.AST_MISSING_ROOT,
                            message=f"Failed to deserialise dict into ASTRoot model: {ex}",
                            field_path=f"{field_prefix}.ast_root",
                        )
                    )

        return errors, warnings


class RequirementsValidator:
    """Validates a ParserResult against configurable ValidationRequirements rule sets."""

    @staticmethod
    def validate(
        result: ParserResult,
        requirements: ValidationRequirements,
    ) -> Tuple[List[ValidationErrorItem], List[ValidationWarningItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if not requirements.allow_syntax_errors and result.status == ParserStatus.SYNTAX_ERROR:
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.REQUIREMENT_FAILED,
                    message="ValidationRequirements disallows SYNTAX_ERROR status.",
                    field_path="parser_result.status",
                )
            )

        if requirements.require_ast and result.status in (ParserStatus.SUCCESS, ParserStatus.PARTIAL_SUCCESS):
            if result.ast_root is None:
                errors.append(
                    ValidationErrorItem(
                        code=ValidationIssueCode.STATUS_AST_MISMATCH,
                        message="ValidationRequirements requires ast_root for successful parse results, but ast_root is None.",
                        field_path="parser_result.ast_root",
                    )
                )

        if requirements.max_duration_ms is not None:
            if result.statistics.duration_ms > requirements.max_duration_ms:
                errors.append(
                    ValidationErrorItem(
                        code=ValidationIssueCode.PARSE_TIMEOUT_EXCEEDED,
                        message=f"Parse duration ({result.statistics.duration_ms:.2f} ms) exceeded maximum allowed threshold ({requirements.max_duration_ms:.2f} ms).",
                        field_path="parser_result.statistics.duration_ms",
                    )
                )

        if requirements.allowed_languages is not None:
            lang_str = result.language.value.lower()
            allowed_set = {l.lower() for l in requirements.allowed_languages}
            if lang_str not in allowed_set:
                errors.append(
                    ValidationErrorItem(
                        code=ValidationIssueCode.LANGUAGE_UNSUPPORTED,
                        message=f"Language '{result.language.value}' is not in the allowed languages whitelist ({', '.join(sorted(allowed_set))}).",
                        field_path="parser_result.language",
                    )
                )

        if requirements.require_docstrings and not result.metadata.capabilities.supports_docstring_extraction:
            warnings.append(
                ValidationWarningItem(
                    code=ValidationIssueCode.DOCSTRING_EXTRACTION_MISSING,
                    message="Parser does not declare supports_docstring_extraction capabilities.",
                    field_path="parser_result.metadata.capabilities.supports_docstring_extraction",
                )
            )

        if requirements.min_semver is not None and result.metadata.version.semver:
            req_ver = requirements.min_semver.strip()
            actual_ver = result.metadata.version.semver.strip()
            # Simple tuple semver compare if both valid
            m_req = SEMVER_REGEX.match(req_ver)
            m_act = SEMVER_REGEX.match(actual_ver)
            if m_req and m_act:
                t_req = (int(m_req.group("major")), int(m_req.group("minor")), int(m_req.group("patch")))
                t_act = (int(m_act.group("major")), int(m_act.group("minor")), int(m_act.group("patch")))
                if t_act < t_req:
                    errors.append(
                        ValidationErrorItem(
                            code=ValidationIssueCode.REQUIREMENT_FAILED,
                            message=f"Parser version {actual_ver} is below required minimum version {req_ver}.",
                            field_path="parser_result.metadata.version.semver",
                        )
                    )

        return errors, warnings


class ParserValidator:
    """
    Unified, thread-safe facade coordinator for the Parser Validation Framework.

    Provides synchronous and asynchronous validation methods for ParserResult, ASTRoot,
    DiagnosticCollection, ParserMetadata, ParserCapabilities, ParserVersion, and ParserLanguage.
    """

    def __init__(self, default_requirements: Optional[ValidationRequirements] = None) -> None:
        self.default_requirements: ValidationRequirements = default_requirements or ValidationRequirements()

    def validate_result(
        self,
        result: ParserResult,
        requirements: Optional[ValidationRequirements] = None,
    ) -> ValidationReport:
        """
        Validate a full `ParserResult` object including nested metadata, statistics, AST,
        and contractual operational requirements.
        """
        start_time = time.perf_counter()
        reqs = requirements or self.default_requirements

        errors, warnings = ParserResultValidator.validate(
            result,
            strict_parent_links=reqs.strict_parent_links,
            strict_range_containment=reqs.strict_range_containment,
        )

        # Operational requirements validation
        req_errors, req_warnings = RequirementsValidator.validate(result, reqs)
        errors.extend(req_errors)
        warnings.extend(req_warnings)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        checked_count = 1 + len(errors) + len(warnings)

        report = ValidationReport(
            is_valid=(len(errors) == 0),
            errors=errors,
            warnings=warnings,
            checked_count=checked_count,
            duration_ms=duration_ms,
        )

        logger.debug(
            f"[ParserValidator] Validated ParserResult for '{result.file_path}' "
            f"in {duration_ms:.2f}ms (is_valid={report.is_valid}, errors={len(errors)}, warnings={len(warnings)})"
        )
        return report

    async def validate_result_async(
        self,
        result: ParserResult,
        requirements: Optional[ValidationRequirements] = None,
    ) -> ValidationReport:
        """Asynchronous wrapper for `validate_result`."""
        return await asyncio.to_thread(self.validate_result, result, requirements)

    def validate_ast(
        self,
        ast: Union[ASTRoot, ASTNode],
        strict_parent_links: bool = True,
        strict_range_containment: bool = True,
    ) -> ValidationReport:
        """Validate an `ASTRoot` or single `ASTNode` tree hierarchy."""
        start_time = time.perf_counter()
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if isinstance(ast, ASTRoot):
            errors, warnings = ASTValidator.validate_root(
                ast,
                strict_parent_links=strict_parent_links,
                strict_range_containment=strict_range_containment,
            )
        elif isinstance(ast, ASTNode):
            n_errs, n_warns, _, _ = ASTValidator.validate_node(
                ast,
                parent=None,
                strict_parent_links=strict_parent_links,
                strict_range_containment=strict_range_containment,
            )
            errors.extend(n_errs)
            warnings.extend(n_warns)
        else:
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.INVALID_TYPE,
                    message=f"Expected ASTRoot or ASTNode instance, got {type(ast).__name__}.",
                    field_path="ast",
                )
            )

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ValidationReport(
            is_valid=(len(errors) == 0),
            errors=errors,
            warnings=warnings,
            checked_count=len(errors) + len(warnings) + 1,
            duration_ms=duration_ms,
        )

    async def validate_ast_async(
        self,
        ast: Union[ASTRoot, ASTNode],
        strict_parent_links: bool = True,
        strict_range_containment: bool = True,
    ) -> ValidationReport:
        """Asynchronous wrapper for `validate_ast`."""
        return await asyncio.to_thread(self.validate_ast, ast, strict_parent_links, strict_range_containment)

    def validate_diagnostics(
        self,
        diagnostics: Union[DiagnosticCollection, List[Diagnostic], Diagnostic],
    ) -> ValidationReport:
        """Validate diagnostics records or collections."""
        start_time = time.perf_counter()
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if isinstance(diagnostics, DiagnosticCollection):
            errors, warnings = DiagnosticsValidator.validate_collection(diagnostics)
        elif isinstance(diagnostics, list):
            for idx, d in enumerate(diagnostics):
                d_errs, d_warns = DiagnosticsValidator.validate_diagnostic(d, field_prefix=f"diagnostics[{idx}]")
                errors.extend(d_errs)
                warnings.extend(d_warns)
        elif isinstance(diagnostics, Diagnostic):
            errors, warnings = DiagnosticsValidator.validate_diagnostic(diagnostics)
        else:
            errors.append(
                ValidationErrorItem(
                    code=ValidationIssueCode.INVALID_TYPE,
                    message=f"Unsupported diagnostics type: {type(diagnostics).__name__}.",
                    field_path="diagnostics",
                )
            )

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ValidationReport(
            is_valid=(len(errors) == 0),
            errors=errors,
            warnings=warnings,
            checked_count=len(errors) + len(warnings) + 1,
            duration_ms=duration_ms,
        )

    def validate_metadata(self, metadata: ParserMetadata) -> ValidationReport:
        """Validate parser engine metadata."""
        start_time = time.perf_counter()
        errors, warnings = MetadataValidator.validate(metadata)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ValidationReport(
            is_valid=(len(errors) == 0),
            errors=errors,
            warnings=warnings,
            checked_count=len(errors) + len(warnings) + 1,
            duration_ms=duration_ms,
        )

    def validate_capabilities(self, capabilities: ParserCapabilities) -> ValidationReport:
        """Validate parser capabilities."""
        start_time = time.perf_counter()
        errors, warnings = CapabilitiesValidator.validate(capabilities)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ValidationReport(
            is_valid=(len(errors) == 0),
            errors=errors,
            warnings=warnings,
            checked_count=len(errors) + len(warnings) + 1,
            duration_ms=duration_ms,
        )

    def validate_version(self, version: ParserVersion) -> ValidationReport:
        """Validate parser semver, ABI, and grammar version."""
        start_time = time.perf_counter()
        errors, warnings = VersionValidator.validate(version)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ValidationReport(
            is_valid=(len(errors) == 0),
            errors=errors,
            warnings=warnings,
            checked_count=len(errors) + len(warnings) + 1,
            duration_ms=duration_ms,
        )

    def validate_language(self, language: ParserLanguage, file_path: Optional[str] = None) -> ValidationReport:
        """Validate language enum and file extension alignment."""
        start_time = time.perf_counter()
        errors, warnings = LanguageValidator.validate(language, file_path=file_path)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ValidationReport(
            is_valid=(len(errors) == 0),
            errors=errors,
            warnings=warnings,
            checked_count=len(errors) + len(warnings) + 1,
            duration_ms=duration_ms,
        )
