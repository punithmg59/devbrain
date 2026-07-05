from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict


class ChangeIntelligenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, description="The engineering question to analyze")


class ChangeIntelligenceError(BaseModel):
    code: str = Field(..., description="Stable machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured details")


class ChangeIntelligenceResponse(BaseModel):
    report: Dict[str, Any] = Field(..., description="The generated EngineeringReport payload")
    timing: Dict[str, float] = Field(default_factory=dict, description="Optional timing metrics for debugging")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
