from pydantic import BaseModel, ConfigDict, field_validator


class AnalysisTriggerResponse(BaseModel):
    repo_id: str
    status: str
    message: str


class AnalysisStatusResponse(BaseModel):
    repo_id: str
    full_name: str
    analysis_status: str
    total_files: int
    total_functions: int
    total_lines: int
    last_analyzed_at: str | None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("repo_id", "last_analyzed_at", mode="before")
    @classmethod
    def to_str(cls, v: object) -> str | None:
        if v is None:
            return None
        return str(v)
 