"""
Engineering Report Schema (Layer 4)

Strongly typed models for the final presentation-ready report.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field


class HeroSectionModel(BaseModel):
    """The Hero section containing the top-level verdict and risk."""
    verdict: str = Field(..., description="The primary decision verdict")
    risk_level: str = Field(..., description="Risk level string")
    risk_score: int = Field(..., description="Risk score 0-100")
    confidence: float = Field(..., description="Overall confidence 0-1.0")


class ReportSectionModel(BaseModel):
    """A single modular section in the report."""
    type: str = Field(..., description="The type identifier for the section (e.g. 'impact', 'evidence')")
    title: str = Field(..., description="Human-readable title of the section")
    priority: int = Field(..., description="Sort order for rendering. Lower is higher priority.")
    content: Dict[str, Any] = Field(..., description="The structured content of the section")


class EngineeringReport(BaseModel):
    """The final structured Engineering Report for DevBrain UI."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the report")
    title: str = Field(..., description="Title of the report")
    intent: str = Field(..., description="The original intent type")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    hero: HeroSectionModel = Field(..., description="The top-level summary metrics")
    sections: List[ReportSectionModel] = Field(default_factory=list, description="Ordered list of modular sections")
    
    next_actions: List[str] = Field(default_factory=list, description="Top-level next actions for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible metadata block")
