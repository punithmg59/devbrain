"""Schemas for repo-detail browsing, file-tree, node exploration, and Groq summaries."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


# ── Folder ──────────────────────────────────────────────────────

class FolderResponse(BaseModel):
    id: str
    repo_id: str
    folder_path: str
    folder_name: str
    parent_path: Optional[str]
    depth: int
    file_count: int
    function_count: int

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "repo_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)


# ── File ────────────────────────────────────────────────────────

class FileResponse(BaseModel):
    id: str
    repo_id: str
    file_path: str
    file_name: str
    extension: Optional[str]
    language: Optional[str]
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


# ── Node ────────────────────────────────────────────────────────

class NodeResponse(BaseModel):
    id: str
    repo_id: str
    file_id: Optional[str]
    node_type: str
    name: str
    full_path: str
    start_line: Optional[int]
    end_line: Optional[int]
    raw_code: Optional[str] = None
    signature: Optional[str]
    calls: List[str]
    called_by: List[str]
    http_method: Optional[str]
    route_path: Optional[str]
    summary: Optional[str]
    tags: List[str]
    is_exported: bool
    is_async: bool
    complexity_score: float

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "repo_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

    @field_validator("file_id", mode="before")
    @classmethod
    def file_id_to_str(cls, v: object) -> Optional[str]:
        return str(v) if v is not None else None


# ── Edge ────────────────────────────────────────────────────────

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


# ── Repo detail ─────────────────────────────────────────────────

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


# ── File tree ───────────────────────────────────────────────────

class FileTreeNode(BaseModel):
    """Used to build the sidebar file tree."""

    id: str
    name: str
    path: str
    type: str  # "file" or "folder"
    depth: int
    children: List["FileTreeNode"] = []
    file_count: Optional[int] = None       # for folders
    function_count: Optional[int] = None   # for folders
    extension: Optional[str] = None        # for files
    language: Optional[str] = None         # for files
    line_count: Optional[int] = None       # for files

    model_config = ConfigDict(from_attributes=True)


FileTreeNode.model_rebuild()


# ── Paginated list wrappers ─────────────────────────────────────

class PaginatedFilesResponse(BaseModel):
    files: List[FileResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class PaginatedNodesResponse(BaseModel):
    nodes: List[NodeResponse]
    total: int
    page: int
    limit: int
    has_more: bool


# ── Single-entity detail wrappers ───────────────────────────────

class FileDetailResponse(BaseModel):
    file: FileResponse
    nodes: List[NodeResponse]


class NodeRelation(BaseModel):
    node_id: str
    name: str
    type: str
    file_path: str


class NodeDetailResponse(BaseModel):
    node: NodeResponse
    file: Optional[FileResponse]
    calls: List[NodeRelation]
    called_by: List[NodeRelation]


# ── Stats ───────────────────────────────────────────────────────

class RepoStatsResponse(BaseModel):
    node_types: dict[str, int]
    extensions: dict[str, int]
    languages: dict[str, int]
    top_files_by_size: List[FileResponse]
    top_complex_nodes: List[NodeResponse]
    total_edges: int
    total_api_routes: int


# ── API routes ──────────────────────────────────────────────────

class ApiRoutesResponse(BaseModel):
    routes: List[NodeResponse]
    total: int


# ── Groq summaries ──────────────────────────────────────────────

class NodeSummaryRequest(BaseModel):
    node_id: str


class NodeSummaryResponse(BaseModel):
    node_id: str
    summary: str
    tags: List[str]


class BatchSummarizeResponse(BaseModel):
    message: str
    nodes_to_process: int
