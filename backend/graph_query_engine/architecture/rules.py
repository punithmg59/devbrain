"""
Architectural Rules Definitions.

Defines rules enforced by the static Architecture Validator.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence


class RuleSeverity(StrEnum):
    """Severity classification for architecture rule violations."""
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True)
class ArchitectureRuleViolation:
    """
    Represents a single architectural boundary or rule violation.
    """
    rule_name: str
    file_path: str
    line_number: int
    message: str
    severity: RuleSeverity = RuleSeverity.ERROR


__all__ = ["RuleSeverity", "ArchitectureRuleViolation"]
