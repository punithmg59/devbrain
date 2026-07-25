"""
core/symbol_builder/validator.py
---------------------------------
Pipeline Contract and Output Integrity Validator.
"""

from __future__ import annotations

from core.symbol_builder.diagnostics import PipelineDiagnostics
from core.symbol_builder.models import SEMANTIC_REPOSITORY_VERSION, SemanticRepository


class PipelineValidator:
    """
    Validates structural consistency and contract integrity of a SemanticRepository.
    """

    @classmethod
    def validate(cls, repo: SemanticRepository) -> PipelineDiagnostics:
        diagnostics = repo.diagnostics

        # 1. Version check
        if repo.version != SEMANTIC_REPOSITORY_VERSION:
            diagnostics = diagnostics.add_pipeline_error(
                message=f"SemanticRepository version '{repo.version}' mismatch with expected '{SEMANTIC_REPOSITORY_VERSION}'.",
                stage_name="PipelineValidator",
                code="ERR_VERSION_MISMATCH"
            )

        # 2. Repository ID matching across stages
        repo_id = repo.repository_id
        if repo.namespace_tree.repository_id != repo_id:
            diagnostics = diagnostics.add_pipeline_error(
                message=f"NamespaceTree repo_id '{repo.namespace_tree.repository_id}' mismatch with expected '{repo_id}'.",
                stage_name="PipelineValidator",
                code="ERR_REPO_ID_MISMATCH"
            )

        if repo.canonical_symbols.repository_id != repo_id:
            diagnostics = diagnostics.add_pipeline_error(
                message=f"CanonicalSymbolCollection repo_id '{repo.canonical_symbols.repository_id}' mismatch with expected '{repo_id}'.",
                stage_name="PipelineValidator",
                code="ERR_REPO_ID_MISMATCH"
            )

        if repo.symbol_table.repository_id != repo_id:
            diagnostics = diagnostics.add_pipeline_error(
                message=f"SymbolTable repo_id '{repo.symbol_table.repository_id}' mismatch with expected '{repo_id}'.",
                stage_name="PipelineValidator",
                code="ERR_REPO_ID_MISMATCH"
            )

        # 3. Symbol count consistency check
        can_count = len(repo.canonical_symbols.symbols)
        tab_count = repo.symbol_table.count()
        if can_count != tab_count:
            diagnostics = diagnostics.add_pipeline_error(
                message=f"Canonical symbols count ({can_count}) mismatch with SymbolTable count ({tab_count}).",
                stage_name="PipelineValidator",
                code="ERR_SYMBOL_COUNT_MISMATCH"
            )

        return diagnostics
