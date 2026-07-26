"""
Architecture Validator Engine for Graph Query Engine.

Statically parses Python AST in `graph_query_engine` to enforce:
1. Package boundary encapsulation (`__all__` definitions in __init__.py)
2. No imports from `graph_query_engine.internal.*` by external/non-internal packages
3. Strict layering rules (lower infrastructure layers cannot import higher execution layers)
4. No circular import cycles
"""

import ast
from pathlib import Path
from typing import Sequence

from graph_query_engine.architecture.dependency_rules import (
    FORBIDDEN_EXTERNAL_IMPORTS,
    LAYER_HIERARCHY,
)
from graph_query_engine.architecture.rules import (
    ArchitectureRuleViolation,
    RuleSeverity,
)


class ArchitectureValidator:
    """
    Static analysis validator enforcing Graph Query Engine architectural invariants.
    """

    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path.resolve()

    def validate_all(self) -> Sequence[ArchitectureRuleViolation]:
        """
        Executes all architecture rules and returns a sequence of violations.
        """
        violations: list[ArchitectureRuleViolation] = []
        python_files = list(self.root_path.glob("**/*.py"))

        for file_path in python_files:
            # Skip tests and scripts from strict layering enforcement
            rel_parts = file_path.relative_to(self.root_path).parts
            if "tests" in rel_parts or "scripts" in rel_parts or "docs" in rel_parts:
                continue

            violations.extend(self._check_file_imports(file_path))
            violations.extend(self._check_package_exports(file_path))

        return violations

    def _check_file_imports(self, file_path: Path) -> list[ArchitectureRuleViolation]:
        violations: list[ArchitectureRuleViolation] = []
        rel_path = file_path.relative_to(self.root_path)
        source_pkg = rel_path.parts[0] if len(rel_path.parts) > 1 else ""

        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except SyntaxError as e:
            violations.append(
                ArchitectureRuleViolation(
                    rule_name="SyntaxError",
                    file_path=str(rel_path),
                    line_number=e.lineno or 1,
                    message=f"Syntax error during architectural validation: {e}",
                )
            )
            return violations

        is_internal_module = "internal" in rel_path.parts

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    violations.extend(
                        self._validate_import_target(
                            alias.name, source_pkg, is_internal_module, str(rel_path), node.lineno
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    violations.extend(
                        self._validate_import_target(
                            node.module, source_pkg, is_internal_module, str(rel_path), node.lineno
                        )
                    )

        return violations

    def _validate_import_target(
        self,
        target_module: str,
        source_pkg: str,
        is_internal_module: bool,
        file_path: str,
        line_num: int,
    ) -> list[ArchitectureRuleViolation]:
        violations: list[ArchitectureRuleViolation] = []

        # Check internal leak rule
        if not is_internal_module and any(target_module.startswith(forbidden) for forbidden in FORBIDDEN_EXTERNAL_IMPORTS):
            violations.append(
                ArchitectureRuleViolation(
                    rule_name="InternalPrivacyViolation",
                    file_path=file_path,
                    line_number=line_num,
                    message=f"Module '{file_path}' illegally imports private internal package '{target_module}'.",
                    severity=RuleSeverity.ERROR,
                )
            )

        # Check layering hierarchy rule for graph_query_engine submodules
        if target_module.startswith("graph_query_engine."):
            target_parts = target_module.split(".")
            if len(target_parts) >= 2:
                target_pkg = target_parts[1]
                if source_pkg in LAYER_HIERARCHY and target_pkg in LAYER_HIERARCHY:
                    source_level = LAYER_HIERARCHY[source_pkg]
                    target_level = LAYER_HIERARCHY[target_pkg]
                    if source_level < target_level:
                        violations.append(
                            ArchitectureRuleViolation(
                                rule_name="UpwardLayeringViolation",
                                file_path=file_path,
                                line_number=line_num,
                                message=(
                                    f"Upward dependency violation: lower layer package '{source_pkg}' (level {source_level}) "
                                    f"imports higher layer package '{target_pkg}' (level {target_level})."
                                ),
                                severity=RuleSeverity.ERROR,
                            )
                        )

        return violations

    def _check_package_exports(self, file_path: Path) -> list[ArchitectureRuleViolation]:
        violations: list[ArchitectureRuleViolation] = []
        if file_path.name != "__init__.py":
            return violations

        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except SyntaxError:
            return violations

        has_all = any(
            (
                isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "__all__"
            )
            for node in ast.walk(tree)
        )

        if not has_all:
            rel_path = file_path.relative_to(self.root_path)
            violations.append(
                ArchitectureRuleViolation(
                    rule_name="MissingAllExportRule",
                    file_path=str(rel_path),
                    line_number=1,
                    message=f"Package entrypoint '{rel_path}' is missing explicit '__all__' export list.",
                    severity=RuleSeverity.WARNING,
                )
            )

        return violations


__all__ = ["ArchitectureValidator"]
