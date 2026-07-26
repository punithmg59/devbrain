"""
Domain enums for Graph Storage.
"""

from enum import Enum, auto


class ConsistencyModel(Enum):
    """Supported consistency models for storage operations."""
    STRONG = auto()
    EVENTUAL = auto()
    LOCAL = auto()
    DISTRIBUTED = auto()


class LogLevel(Enum):
    """Logging severity levels for storage diagnostics."""
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


class ProbePolicy(Enum):
    """Probe evaluation policy for storage health providers."""
    READ_ONLY = auto()
    READ_WRITE = auto()
    FULL = auto()
