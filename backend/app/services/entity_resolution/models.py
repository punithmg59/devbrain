"""Entity Resolution data models."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID


class EngineeringAction(str, Enum):
    """Engineering action types extracted from natural language."""
    DELETE = "delete"
    RENAME = "rename"
    MOVE = "move"
    ADD = "add"
    EXTRACT = "extract"
    EXPLAIN = "explain"
    FIND = "find"


class TargetType(str, Enum):
    """Target entity types."""
    FUNCTION = "function"
    CLASS = "class"
    SERVICE = "service"
    FILE = "file"
    MODULE = "module"
    API = "api"
    API_ROUTE = "api_route"
    DATABASE_TABLE = "database_table"
    WORKFLOW = "workflow"
    UNKNOWN = "unknown"


@dataclass
class RepositoryNode:
    """Canonical representation of a resolved repository node."""
    id: UUID
    name: str
    node_type: TargetType
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    repo_id: Optional[UUID] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "name": self.name,
            "node_type": self.node_type.value,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "repo_id": str(self.repo_id) if self.repo_id else None
        }


@dataclass
class EntityExtraction:
    """Result of entity extraction from natural language."""
    action: Optional[EngineeringAction]
    target_name: Optional[str]
    target_type: Optional[TargetType]
    raw_query: str
    confidence: float

    def is_valid(self) -> bool:
        """Check if extraction produced valid results."""
        return self.action is not None and self.target_name is not None


@dataclass
class ResolutionResult:
    """Result of repository node resolution."""
    node: Optional[RepositoryNode]
    success: bool
    match_type: str  # "exact", "case_insensitive", "fuzzy", "none"
    suggested_matches: list[dict]
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "node": self.node.to_dict() if self.node else None,
            "success": self.success,
            "match_type": self.match_type,
            "suggested_matches": self.suggested_matches,
            "error_message": self.error_message
        }
