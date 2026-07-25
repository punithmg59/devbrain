"""
core/facade Package
-------------------
DependencyGraph Facade - Final Public Entrypoint for DevBrain Repository Analyzer V2.
"""

from core.facade.exceptions import (
    FacadeError,
    FacadePipelineError,
    FacadeSerializationError,
)
from core.facade.facade import DependencyGraphFacade
from core.facade.interfaces import (
    IDependencyGraphFacade,
    IRepositoryAnalysisResult,
)
from core.facade.models import RepositoryAnalysisResult
from core.facade.serialization import (
    ANALYSIS_RESULT_VERSION,
    analysis_result_to_dict,
    analysis_result_to_json,
    dict_to_analysis_result,
    hash_analysis_result,
    json_to_analysis_result,
)

__all__ = [
    # Main Public Facade & Result Model
    "DependencyGraphFacade",
    "RepositoryAnalysisResult",
    # Interfaces
    "IDependencyGraphFacade",
    "IRepositoryAnalysisResult",
    # Exceptions
    "FacadeError",
    "FacadePipelineError",
    "FacadeSerializationError",
    # Serialization
    "ANALYSIS_RESULT_VERSION",
    "analysis_result_to_dict",
    "dict_to_analysis_result",
    "analysis_result_to_json",
    "json_to_analysis_result",
    "hash_analysis_result",
]
