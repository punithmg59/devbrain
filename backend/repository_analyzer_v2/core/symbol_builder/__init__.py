"""
core/symbol_builder Package
----------------------------
Symbol Builder Facade and SemanticRepository orchestrator for DevBrain.
"""

from core.symbol_builder.builder import SymbolBuilder
from core.symbol_builder.diagnostics import (
    PipelineDiagnosticRecord,
    PipelineDiagnostics,
)
from core.symbol_builder.exceptions import (
    PipelineError,
    PipelineSerializationError,
    PipelineValidationError,
    StageExecutionError,
)
from core.symbol_builder.interfaces import (
    ISemanticRepository,
    ISymbolBuilderFacade,
)
from core.symbol_builder.models import (
    SEMANTIC_REPOSITORY_VERSION,
    SemanticRepository,
)
from core.symbol_builder.pipeline import SymbolPipelineEngine
from core.symbol_builder.serialization import (
    dict_to_semantic_repository,
    hash_semantic_repository,
    json_to_semantic_repository,
    semantic_repository_to_dict,
    semantic_repository_to_json,
)
from core.symbol_builder.statistics import SemanticRepositoryStatistics
from core.symbol_builder.validator import PipelineValidator

__all__ = [
    # Facade & Main Entity
    "SymbolBuilder",
    "SemanticRepository",
    "SEMANTIC_REPOSITORY_VERSION",
    # Engine & Models
    "SymbolPipelineEngine",
    "SemanticRepositoryStatistics",
    # Diagnostics & Validation
    "PipelineDiagnosticRecord",
    "PipelineDiagnostics",
    "PipelineValidator",
    # Interfaces
    "ISemanticRepository",
    "ISymbolBuilderFacade",
    # Exceptions
    "PipelineError",
    "StageExecutionError",
    "PipelineValidationError",
    "PipelineSerializationError",
    # Serialization
    "semantic_repository_to_dict",
    "dict_to_semantic_repository",
    "semantic_repository_to_json",
    "json_to_semantic_repository",
    "hash_semantic_repository",
]
