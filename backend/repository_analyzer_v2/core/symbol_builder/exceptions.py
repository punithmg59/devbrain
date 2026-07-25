"""
core/symbol_builder/exceptions.py
----------------------------------
Domain exceptions for Symbol Builder Facade & SemanticRepository.
"""


class PipelineError(Exception):
    """Base exception for all symbol pipeline execution errors."""
    pass


class StageExecutionError(PipelineError):
    """Raised when a specific pipeline stage fails execution."""
    pass


class PipelineValidationError(PipelineError):
    """Raised when pipeline contract validation or output verification fails."""
    pass


class PipelineSerializationError(PipelineError):
    """Raised when SemanticRepository serialization or deserialization fails."""
    pass
