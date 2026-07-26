"""
BackendType enum for Graph Storage backends.
"""

from enum import Enum, auto


class BackendType(Enum):
    LOCAL = auto()
    MEMORY = auto()
    S3 = auto()
    GCS = auto()
    AZURE = auto()
