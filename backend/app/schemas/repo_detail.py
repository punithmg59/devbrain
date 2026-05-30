from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator

class FolderResponse(BaseModel):
    id: str
    repo_id: str
    folder_path: str
    folder_name: str
    parent_path: Optional[str] = None
    depth: int
    file_count: int
    function_count: int
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "repo_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

class FileResponse(BaseModel):
    id: str
    repo_id: str
    file_path: str
    file_name: str
    extension: Optional[str] = None
    language: Optional[str] = None
    folder_path: str
    depth: int
    size_bytes: int
    line_count: int
    content_preview: Optional[str] = None
    importance_score: float
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "repo_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

class NodeResponse(BaseModel):
    id: str
    repo_id: str
    file_id: Optional[str] = None
    node_type: str
    name: str
    full_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    raw_code: Optional[str] = None
    signature: Optional[str] = None
    calls: List[str] = []
    called_by: List[str] = []
    http_method: Optional[str] = None
    route_path: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = []
    is_exported: bool = False
    is_async: bool = False
    complexity_score: float = 0.0
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "repo_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

    @field_validator("file_id", mode="before")
    @classmethod
    def file_id_to_str(cls, v: object) -> Optional[str]:
        return str(v) if v is not None else None

class EdgeResponse(BaseModel):
    id: str
    from_node_id: str
    to_node_id: str
    edge_type: str
    weight: float
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "from_node_id", "to_node_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

class FileTreeItem(BaseModel):
    id: str
    name: str
    path: str
    type: str  # "file" or "folder"
    depth: int
    children: List['FileTreeItem'] = []
    file_count: Optional[int] = None
    function_count: Optional[int] = None
    extension: Optional[str] = None
    language: Optional[str] = None
    line_count: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

FileTreeItem.model_rebuild()

class PaginatedFiles(BaseModel):
    files: List[FileResponse]
    total: int
    page: int
    limit: int
    has_more: bool
    model_config = ConfigDict(from_attributes=True)

class PaginatedNodes(BaseModel):
    nodes: List[NodeResponse]
    total: int
    page: int
    limit: int
    has_more: bool
    model_config = ConfigDict(from_attributes=True)

class FileWithNodes(BaseModel):
    file: FileResponse
    nodes: List[NodeResponse]
    model_config = ConfigDict(from_attributes=True)

class NodeWithRelations(BaseModel):
    node: NodeResponse
    file: Optional[FileResponse] = None
    calls: List[dict] = []
    called_by: List[dict] = []
    model_config = ConfigDict(from_attributes=True)

class RepoStats(BaseModel):
    node_types: dict
    extensions: dict
    languages: dict
    top_files_by_size: List[FileResponse]
    top_complex_nodes: List[NodeResponse]
    total_edges: int
    total_api_routes: int
    model_config = ConfigDict(from_attributes=True)

class NodeSummaryRequest(BaseModel):
    force: bool = False
    model_config = ConfigDict(from_attributes=True)

class NodeSummaryResponse(BaseModel):
    node_id: str
    summary: str
    tags: List[str]
    model_config = ConfigDict(from_attributes=True)

# ── Compatibility Aliases and Extra Classes for Router ──
FileTreeNode = FileTreeItem
PaginatedFilesResponse = PaginatedFiles
PaginatedNodesResponse = PaginatedNodes
FileDetailResponse = FileWithNodes
NodeDetailResponse = NodeWithRelations
RepoStatsResponse = RepoStats

class NodeRelation(BaseModel):
    node_id: str
    name: str
    type: str
    file_path: str
    model_config = ConfigDict(from_attributes=True)

class RepoDetailResponse(BaseModel):
    id: str
    full_name: str
    name: str
    description: Optional[str]
    language: Optional[str]
    analysis_status: str
    last_analyzed_at: Optional[datetime]
    total_files: int
    total_functions: int
    total_lines: int
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

class ApiRoutesResponse(BaseModel):
    routes: List[NodeResponse]
    total: int
    model_config = ConfigDict(from_attributes=True)

class BatchSummarizeResponse(BaseModel):
    message: str
    nodes_to_process: int
    model_config = ConfigDict(from_attributes=True)
