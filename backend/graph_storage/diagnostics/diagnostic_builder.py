"""
DiagnosticBuilder pattern implementation.
"""

import time
from typing import Dict, List, Optional

from graph_storage.diagnostics.health_monitor import HealthReport
from graph_storage.diagnostics.storage_diagnostics import DiagnosticReport, SystemStatistics
from graph_storage.exceptions import GraphStorageError


class DiagnosticBuilder:
    """Builder pattern for constructing HealthReport, DiagnosticReport, and SystemStatistics."""

    def __init__(self):
        self._findings: List[str] = []
        self._warnings: List[str] = []
        self._errors: List[str] = []
        self._recommendations: List[str] = []
        self._severity: str = "INFO"

    def add_finding(self, finding: str) -> "DiagnosticBuilder":
        self._findings.append(finding)
        return self

    def add_warning(self, warning: str) -> "DiagnosticBuilder":
        self._warnings.append(warning)
        return self

    def add_error(self, error: str) -> "DiagnosticBuilder":
        self._errors.append(error)
        return self

    def add_recommendation(self, recommendation: str) -> "DiagnosticBuilder":
        self._recommendations.append(recommendation)
        return self

    def set_severity(self, severity: str) -> "DiagnosticBuilder":
        self._severity = severity
        return self

    def build_diagnostic_report(self) -> DiagnosticReport:
        return DiagnosticReport(
            findings=list(self._findings),
            warnings=list(self._warnings),
            errors=list(self._errors),
            recommendations=list(self._recommendations),
            severity=self._severity,
            timestamp=time.time(),
        )

    def build_health_report(self, overall_health: str = "HEALTHY") -> HealthReport:
        return HealthReport(
            overall_health=overall_health,
            warnings=list(self._warnings),
            errors=list(self._errors),
            recommendations=list(self._recommendations),
            timestamp=time.time(),
        )
