"""
Immutable BaseIndex Parent Model for Graph Query Engine.
"""

from typing import Any, Iterable
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.index.descriptor import IndexDescriptor
from graph_query_engine.index.metadata import IndexMetadata
from graph_query_engine.index.statistics import IndexStatistics
from graph_query_engine.view.identity import GraphIdentity


class BaseIndex(BaseModel):
    """
    Immutable base class for all future index implementations in Graph Query Engine.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    index_id: str = Field(..., description="Unique index instance identifier")
    descriptor: IndexDescriptor = Field(..., description="Index descriptor definition")
    metadata: IndexMetadata = Field(..., description="Index provenance metadata")
    statistics: IndexStatistics = Field(..., description="Index metrics snapshot")
    graph_identity: GraphIdentity = Field(..., description="Associated GraphIdentity snapshot reference")

    @property
    def index_name(self) -> str:
        """Returns the index descriptor name."""
        return self.descriptor.name

    def lookup(self, key: Any) -> Iterable[Any]:
        """
        Base lookup contract placeholder. Subclasses override to provide O(1) indexed lookup.
        """
        return ()


__all__ = ["BaseIndex"]
