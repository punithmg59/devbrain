from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, field_validator
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    github_id: str
    username: str
    email: Optional[str]
    avatar_url: Optional[str]
    plan: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def id_to_str(cls, v: object) -> str:
        return str(v)


class SessionResponse(BaseModel):
    user: UserResponse
    message: str
