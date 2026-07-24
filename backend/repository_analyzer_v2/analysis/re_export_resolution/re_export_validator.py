"""
analysis/re_export_resolution/re_export_validator.py
-----------------------------------------------------
Phase 4.7.1 — Re-Export Index Integrity Validator.

Validates the integrity of the ReExportIndex after build, detecting:
- Duplicate exported names within the same package
- Dangling exports with no resolvable source module
- Cyclic re-export chains (A exports B which re-exports A)

Design Principles
-----------------
- **Structured Validation Report**: Returns ReExportValidationReport with breakdowns.
- **Non-Throwing**: Records issues without raising exceptions.
- **Cycle Detection**: DFS cycle detection on package-level re-export graph.
"""

from __future__ import annotations

from typing import Dict, List, Set

from models.re_export_models import (
    ReExportValidationIssue,
    ReExportValidationReport,
)
from analysis.re_export_resolution.re_export_index import ReExportIndex


class ReExportValidator:
    """
    Validator engine for re-export index integrity.

    Usage::

        validator = ReExportValidator()
        report = validator.validate(export_index)
    """

    def validate(self, export_index: ReExportIndex) -> ReExportValidationReport:
        """
        Validate the export index for integrity issues.

        Parameters
        ----------
        export_index:
            Pre-built ReExportIndex.

        Returns
        -------
        ReExportValidationReport
        """
        issues: List[ReExportValidationIssue] = []
        error_count = 0
        warning_count = 0

        # 1. Detect duplicate exported names within same package
        for pkg_fqn, records in export_index._by_package.items():
            seen_names: Dict[str, str] = {}  # name → first export_id
            for rec in records:
                if rec.is_star_export:
                    continue
                if rec.exported_name in seen_names:
                    issues.append(
                        ReExportValidationIssue(
                            severity="warning",
                            code="DUPLICATE_EXPORT",
                            message=(
                                f"Duplicate export '{rec.exported_name}' in package "
                                f"'{pkg_fqn}' (first: {seen_names[rec.exported_name]}, "
                                f"duplicate: {rec.export_id})"
                            ),
                            export_id=rec.export_id,
                            package_fqn=pkg_fqn,
                        )
                    )
                    warning_count += 1
                else:
                    seen_names[rec.exported_name] = rec.export_id

        # 2. Detect exports with no source module (warning only, not error — may resolve at runtime)
        for rec in export_index.records.values():
            if (
                not rec.is_star_export
                and rec.source_module_fqn is None
                and rec.export_type.value in ("from_import", "from_alias")
            ):
                issues.append(
                    ReExportValidationIssue(
                        severity="warning",
                        code="MISSING_SOURCE_MODULE",
                        message=(
                            f"Export '{rec.exported_name}' in package '{rec.package_fqn}' "
                            f"has no resolved source module FQN"
                        ),
                        export_id=rec.export_id,
                        package_fqn=rec.package_fqn,
                    )
                )
                warning_count += 1

        # 3. Cycle detection on package re-export graph
        # Build a directed graph: package_fqn → set of source_module_fqns
        graph: Dict[str, Set[str]] = {}
        for rec in export_index.records.values():
            if rec.source_module_fqn and rec.source_module_fqn != rec.package_fqn:
                graph.setdefault(rec.package_fqn, set()).add(rec.source_module_fqn)

        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycle_reported: Set[str] = set()

        def dfs(node: str, path: List[str]) -> None:
            nonlocal warning_count
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor) if neighbor in path else 0
                    cycle_chain = " → ".join(path[cycle_start:] + [neighbor])
                    if neighbor not in cycle_reported:
                        cycle_reported.add(neighbor)
                        issues.append(
                            ReExportValidationIssue(
                                severity="warning",
                                code="CYCLIC_EXPORT",
                                message=f"Cyclic re-export chain detected: {cycle_chain}",
                                package_fqn=neighbor,
                            )
                        )
                        nonlocal warning_count
                        warning_count += 1

            path.pop()
            rec_stack.discard(node)

        for pkg in list(graph.keys()):
            if pkg not in visited:
                dfs(pkg, [])

        is_valid = error_count == 0
        return ReExportValidationReport(
            is_valid=is_valid,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
        )
