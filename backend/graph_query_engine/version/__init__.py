"""
Graph Query Engine Version Package.

Storage schema evolution and versioning contracts.
"""

from graph_query_engine.version.compatibility import IVersionCompatibilityMatrix
from graph_query_engine.version.future_versions import IFutureVersionStrategy
from graph_query_engine.version.schema_version import ISchemaVersion
from graph_query_engine.version.version import IEngineVersion

__all__ = [
    "IEngineVersion",
    "ISchemaVersion",
    "IVersionCompatibilityMatrix",
    "IFutureVersionStrategy",
]
