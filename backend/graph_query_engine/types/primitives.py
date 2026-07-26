"""
Primitive domain types for the Graph Query Engine.

Provides strongly-typed domain identifiers using Python's NewType and dataclasses.
These value objects are immutable and enforce type safety across the query engine.
"""

from typing import NewType

# Strongly-typed identifier primitives
NodeId = NewType("NodeId", str)
EdgeId = NewType("EdgeId", str)
SymbolId = NewType("SymbolId", str)
FileId = NewType("FileId", str)
NamespaceId = NewType("NamespaceId", str)
PackageId = NewType("PackageId", str)
RepositoryId = NewType("RepositoryId", str)
SnapshotId = NewType("SnapshotId", str)
QueryId = NewType("QueryId", str)
RequestId = NewType("RequestId", str)
CorrelationId = NewType("CorrelationId", str)
LanguageId = NewType("LanguageId", str)
