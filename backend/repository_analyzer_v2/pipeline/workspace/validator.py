"""
pipeline/workspace/validator.py
-------------------------------
Step 1 — Repository Validator Engine.

Performs pre-scan validation checks verifying filesystem access, non-emptiness,
supported structure, and Git HEAD integrity.
"""

from __future__ import annotations

import os
from typing import List

from pipeline.workspace.models import WorkspaceValidationIssue, WorkspaceValidationReport
from utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryValidator:
    """
    Validates target repository structure and permissions before scanning.

    Usage::

        validator = RepositoryValidator()
        report = validator.validate(repo_root)
        if not report.is_valid:
            # Handle invalid repository
    """

    def validate(self, repository_root: str) -> WorkspaceValidationReport:
        """
        Validate repository filesystem access and integrity.

        Parameters
        ----------
        repository_root:
            Absolute path to repository root directory.

        Returns
        -------
        WorkspaceValidationReport
        """
        issues: List[WorkspaceValidationIssue] = []

        # 1. Existence Check
        if not os.path.exists(repository_root):
            issues.append(
                WorkspaceValidationIssue(
                    severity="error",
                    code="REPO_NOT_FOUND",
                    message=f"Repository directory does not exist: '{repository_root}'",
                    file_path=repository_root,
                )
            )
            return WorkspaceValidationReport(
                is_valid=False,
                issues=issues,
                error_count=1,
                warning_count=0,
            )

        # 2. Directory Check
        if not os.path.isdir(repository_root):
            issues.append(
                WorkspaceValidationIssue(
                    severity="error",
                    code="NOT_A_DIRECTORY",
                    message=f"Target path is not a directory: '{repository_root}'",
                    file_path=repository_root,
                )
            )
            return WorkspaceValidationReport(
                is_valid=False,
                issues=issues,
                error_count=1,
                warning_count=0,
            )

        # 3. Read Access Permission Check
        if not os.access(repository_root, os.R_OK):
            issues.append(
                WorkspaceValidationIssue(
                    severity="error",
                    code="PERMISSION_DENIED",
                    message=f"Read permission denied for directory: '{repository_root}'",
                    file_path=repository_root,
                )
            )
            return WorkspaceValidationReport(
                is_valid=False,
                issues=issues,
                error_count=1,
                warning_count=0,
            )

        # 4. Non-Emptiness Check
        try:
            entries = os.listdir(repository_root)
            if not entries:
                issues.append(
                    WorkspaceValidationIssue(
                        severity="error",
                        code="EMPTY_REPOSITORY",
                        message=f"Repository directory is empty: '{repository_root}'",
                        file_path=repository_root,
                    )
                )
        except Exception as exc:
            issues.append(
                WorkspaceValidationIssue(
                    severity="error",
                    code="DIRECTORY_READ_ERROR",
                    message=f"Failed to read directory contents: {exc}",
                    file_path=repository_root,
                )
            )

        # 5. Git Integrity Check (if .git folder exists)
        git_dir = os.path.join(repository_root, ".git")
        if os.path.exists(git_dir):
            git_head = os.path.join(git_dir, "HEAD")
            if not os.path.exists(git_head):
                issues.append(
                    WorkspaceValidationIssue(
                        severity="warning",
                        code="CORRUPTED_GIT_HEAD",
                        message="Repository has .git directory but is missing .git/HEAD file",
                        file_path=".git/HEAD",
                    )
                )

        error_count = len([i for i in issues if i.severity == "error"])
        warning_count = len([i for i in issues if i.severity == "warning"])
        is_valid = error_count == 0

        logger.debug(
            f"[RepositoryValidator] Validated '{repository_root}': "
            f"is_valid={is_valid}, Errors={error_count}, Warnings={warning_count}"
        )

        return WorkspaceValidationReport(
            is_valid=is_valid,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
        )
