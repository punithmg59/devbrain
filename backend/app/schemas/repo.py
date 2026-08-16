from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class GitHubRepoItem(BaseModel):
    github_repo_id: int
    full_name: str
    name: str
    description: str | None
    default_branch: str
    is_private: bool
    language: str | None
    already_connected: bool = False


class ConnectRepoRequest(BaseModel):
    github_repo_id: int


class RepoResponse(BaseModel):
    id: str
    github_repo_id: int
    full_name: str
    name: str
    description: str | None
    default_branch: str
    is_private: bool
    language: str | None
    analysis_status: str
    has_completed_analysis: bool
    total_files: int
    total_functions: int
    total_lines: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "created_at", mode="before")
    @classmethod
    def to_str(cls, v: object) -> str:
        return str(v)
