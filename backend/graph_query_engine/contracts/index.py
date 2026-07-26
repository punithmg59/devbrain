"""
Index Interface Contracts for Graph Query Engine.

CONTRACT ONLY - NO INDEX IMPLEMENTATIONS IN STEP 3.1.
"""

from typing import Any, Iterable, Optional, Protocol

from graph_query_engine.contracts.view import IGraphView


class IIndexDescriptor(Protocol):
    """Contract for index configuration descriptors."""
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def version(self) -> str: ...
    @property
    def supported_graph_version(self) -> str: ...
    @property
    def supported_schema_version(self) -> str: ...
    @property
    def index_type(self) -> str: ...
    @property
    def build_strategy(self) -> str: ...


class IIndexMetadata(Protocol):
    """Contract for index provenance metadata."""
    @property
    def builder_version(self) -> str: ...
    @property
    def source_graph_version(self) -> str: ...
    @property
    def storage_version(self) -> str: ...


class IIndexStatistics(Protocol):
    """Contract for index structural metrics."""
    @property
    def memory_estimate_bytes(self) -> int: ...
    @property
    def node_count(self) -> int: ...
    @property
    def edge_count(self) -> int: ...


class IIndex(Protocol):
    """
    Base contract for all graph indexes.
    """
    @property
    def index_id(self) -> str: ...
    @property
    def index_name(self) -> str: ...
    @property
    def descriptor(self) -> IIndexDescriptor: ...
    @property
    def metadata(self) -> IIndexMetadata: ...
    @property
    def statistics(self) -> IIndexStatistics: ...

    def lookup(self, key: Any) -> Iterable[Any]: ...


class IIndexBuilder(Protocol):
    """Contract for assembling indexes from IGraphView."""
    def build(self, graph_view: IGraphView) -> IIndex: ...


class IIndexFactory(Protocol):
    """Contract for manufacturing validated index instances."""
    def create_index(self, index_type: str, graph_view: IGraphView) -> IIndex: ...


class IIndexLifecycle(Protocol):
    """Contract for managing index lifecycle transitions."""
    def get_state(self) -> str: ...


class IIndexValidator(Protocol):
    """Contract for validating index integrity."""
    def validate(self, index: IIndex) -> Any: ...


class IIndexRegistry(Protocol):
    """Contract for managing registered index types and instances."""
    def register(self, index_name: str, index_cls: Any) -> None: ...
    def get_index(self, name: str) -> Optional[IIndex]: ...
    def has_index(self, name: str) -> bool: ...


class IIndexProvider(Protocol):
    """Contract for dependency-injecting index instances."""
    def provide_index(self, index_name: str) -> Optional[IIndex]: ...


__all__ = [
    "IIndex",
    "IIndexBuilder",
    "IIndexRegistry",
    "IIndexFactory",
    "IIndexLifecycle",
    "IIndexStatistics",
    "IIndexValidator",
    "IIndexMetadata",
    "IIndexDescriptor",
    "IIndexProvider",
]
