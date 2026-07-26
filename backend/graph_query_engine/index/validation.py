"""
Index Validation Framework for Graph Query Engine.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.index.base import BaseIndex


class IndexValidationViolation(BaseModel):
    """Represents a single index validation rule violation."""
    model_config = ConfigDict(frozen=True)

    category: str = Field(..., description="Validation category name")
    rule_name: str = Field(..., description="Specific rule identifier")
    message: str = Field(..., description="Human-readable violation description")
    severity: str = Field(default="ERROR", description="ERROR or WARNING")


class IndexValidationReport(BaseModel):
    """
    Immutable validation quality report for an index instance.
    """
    model_config = ConfigDict(frozen=True)

    is_valid: bool = Field(..., description="True if no ERROR severity violations exist")
    violations: tuple[IndexValidationViolation, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of violations",
    )
    validated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of validation execution",
    )


class IndexValidator:
    """
    Validator inspecting BaseIndex instances across metadata, version, identity, and descriptor rules.
    """

    @classmethod
    def validate(cls, index: Optional[BaseIndex]) -> IndexValidationReport:
        """
        Executes complete validation over an index instance and returns a report.
        """
        violations: list[IndexValidationViolation] = []

        if index is None:
            violations.append(
                IndexValidationViolation(
                    category="EXISTENCE",
                    rule_name="INDEX_NOT_NULL",
                    message="Index instance is null/None.",
                )
            )
            return IndexValidationReport(is_valid=False, violations=tuple(violations))

        if not index.index_id:
            violations.append(
                IndexValidationViolation(
                    category="IDENTITY",
                    rule_name="MISSING_INDEX_ID",
                    message="Index.index_id must not be empty.",
                )
            )

        if not index.descriptor.name:
            violations.append(
                IndexValidationViolation(
                    category="DESCRIPTOR",
                    rule_name="MISSING_DESCRIPTOR_NAME",
                    message="IndexDescriptor.name must not be empty.",
                )
            )

        if not index.graph_identity.snapshot_id:
            violations.append(
                IndexValidationViolation(
                    category="IDENTITY",
                    rule_name="MISSING_GRAPH_SNAPSHOT_ID",
                    message="GraphIdentity.snapshot_id must not be empty.",
                )
            )

        # Future capability & configuration hooks
        cls._validate_version_compatibility(index, violations)
        cls._validate_statistics_bounds(index, violations)
        cls._validate_future_hooks(index, violations)

        is_valid = not any(v.severity == "ERROR" for v in violations)
        return IndexValidationReport(is_valid=is_valid, violations=tuple(violations))

    @classmethod
    def _validate_version_compatibility(cls, index: BaseIndex, violations: list[IndexValidationViolation]) -> None:
        """Placeholder hook for index vs graph version compatibility."""
        pass

    @classmethod
    def _validate_statistics_bounds(cls, index: BaseIndex, violations: list[IndexValidationViolation]) -> None:
        """Placeholder hook for index memory & node count sanity checks."""
        pass

    @classmethod
    def _validate_future_hooks(cls, index: BaseIndex, violations: list[IndexValidationViolation]) -> None:
        """Placeholder hook for future extension capability validation."""
        pass


__all__ = [
    "IndexValidationViolation",
    "IndexValidationReport",
    "IndexValidator",
]
