from typing import List, Optional

from pydantic import BaseModel, Field


class SmartResolvedEntity(BaseModel):
    entity_id: str
    entity_type: str
    name: str
    confidence: int
    reason: str
    source: str
    file_path: Optional[str] = None
    http_method: Optional[str] = None
    route_path: Optional[str] = None
    workflow_name: Optional[str] = None
    graph_connections: List[str] = Field(default_factory=list)


class ResolveRequest(BaseModel):
    query: str
    limit: int = 10


class ResolveResponse(BaseModel):
    query: str
    resolved_entities: List[SmartResolvedEntity]
    primary_entity: Optional[SmartResolvedEntity] = None
    resolution_ms: int = 0


class AutocompleteSuggestion(BaseModel):
    label: str
    entity_type: str
    entity_id: Optional[str] = None
    file_path: Optional[str] = None
    source: str
    subtitle: Optional[str] = None


class AutocompleteResponse(BaseModel):
    suggestions: List[AutocompleteSuggestion]
