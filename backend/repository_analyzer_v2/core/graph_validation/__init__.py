"""
core/graph_validation Package
------------------------------
Dependency Graph Validation Framework for DevBrain Dependency Graph Platform.
"""

from core.graph_validation.diagnostics import (
    ValidationCategory,
    ValidationDiagnostic,
    ValidationDiagnostics,
)
from core.graph_validation.exceptions import (
    GraphValidationError,
    ValidationReportError,
    ValidationSerializationError,
)
from core.graph_validation.interfaces import (
    IDependencyGraphValidationReport,
    IDependencyGraphValidatorFacade,
)
from core.graph_validation.report import DependencyGraphValidationReport
from core.graph_validation.serialization import (
    VALIDATION_REPORT_VERSION,
    dict_to_validation_report,
    hash_validation_report,
    json_to_validation_report,
    validation_report_to_dict,
    validation_report_to_json,
)
from core.graph_validation.statistics import ValidationStatistics
from core.graph_validation.validator import DependencyGraphValidator

__all__ = [
    # Validator & Main Report Domain Model
    "DependencyGraphValidator",
    "DependencyGraphValidationReport",
    "ValidationCategory",
    "ValidationDiagnostic",
    "ValidationDiagnostics",
    "ValidationStatistics",
    # Interfaces
    "IDependencyGraphValidationReport",
    "IDependencyGraphValidatorFacade",
    # Exceptions
    "GraphValidationError",
    "ValidationReportError",
    "ValidationSerializationError",
    # Serialization
    "VALIDATION_REPORT_VERSION",
    "validation_report_to_dict",
    "dict_to_validation_report",
    "validation_report_to_json",
    "json_to_validation_report",
    "hash_validation_report",
]
