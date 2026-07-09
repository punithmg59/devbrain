"""
Custom exceptions for DevBrain production readiness.

Provides specific exception types for better error handling and debugging.
"""


class DevBrainException(Exception):
    """Base exception for all DevBrain errors."""
    pass


class EvidenceValidationError(DevBrainException):
    """Raised when EngineeringEvidence validation fails."""
    pass


class RepositoryDataError(DevBrainException):
    """Raised when repository data collection fails."""
    pass


class IntentClassificationError(DevBrainException):
    """Raised when intent classification fails."""
    pass


class EntityResolutionError(DevBrainException):
    """Raised when entity resolution fails."""
    pass


class ImpactAnalysisError(DevBrainException):
    """Raised when impact analysis fails."""
    pass


class ReferenceIntelligenceError(DevBrainException):
    """Raised when reference intelligence analysis fails."""
    pass


class ReasoningEngineError(DevBrainException):
    """Raised when reasoning engine fails."""
    pass


class SimulationEngineError(DevBrainException):
    """Raised when simulation engine fails."""
    pass


class GraphTraversalError(DevBrainException):
    """Raised when graph traversal fails."""
    pass


class CacheError(DevBrainException):
    """Raised when cache operations fail."""
    pass


class DatabaseError(DevBrainException):
    """Raised when database operations fail."""
    pass


class ConfigurationError(DevBrainException):
    """Raised when configuration is invalid."""
    pass


class NLQEngineError(DevBrainException):
    """Raised when NLQ Engine processing fails."""
    pass


class EngineeringIntelligenceError(DevBrainException):
    """Raised when engineering intelligence generation fails."""
    pass


class ReportComposerError(DevBrainException):
    """Raised when the report composer stage fails."""
    pass
