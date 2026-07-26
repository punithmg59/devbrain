"""
Architecture Validation Package.
"""

from graph_query_engine.architecture.dependency_rules import (
    FORBIDDEN_EXTERNAL_IMPORTS,
    LAYER_HIERARCHY,
)
from graph_query_engine.architecture.rules import (
    ArchitectureRuleViolation,
    RuleSeverity,
)
from graph_query_engine.architecture.validator import ArchitectureValidator

__all__ = [
    "ArchitectureValidator",
    "ArchitectureRuleViolation",
    "RuleSeverity",
    "LAYER_HIERARCHY",
    "FORBIDDEN_EXTERNAL_IMPORTS",
]
