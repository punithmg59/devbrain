"""
Engineering Decision Schema (Layer 3)

Strongly typed models for the Reasoning Engine output.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DecisionType(str, Enum):
    SAFE = "SAFE"
    LOW_IMPACT = "LOW IMPACT"
    MEDIUM_IMPACT = "MEDIUM IMPACT"
    HIGH_IMPACT = "HIGH IMPACT"
    CRITICAL_IMPACT = "CRITICAL IMPACT"
    UNKNOWN = "UNKNOWN"


class EngineeringDecision(BaseModel):
    """
    The main output of the DevBrain Reasoning Engine.
    This JSON object is consumed by UI layers and the future Engineering Report layer.
    """

    # Existing required fields for UI/Report layer
    decision: DecisionType = Field(..., description="The primary engineering decision")
    risk_level: RiskLevel = Field(..., description="Calculated risk severity")
    risk_score: int = Field(..., ge=0, le=100, description="Numerical risk score (0-100)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in the decision")
    
    summary: str = Field(..., description="A short summary of the decision")
    primary_reason: str = Field(..., description="The primary reason for this decision")
    
    affected_components: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    alternative_options: List[str] = Field(default_factory=list)
    required_tests: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)

    # New fields requested by user
    risk_explanation: str = Field("", description="Explanation of the risk level")
    component_importance: str = Field("", description="Why the component is important")
    
    downstream_dependencies: List[str] = Field(default_factory=list, description="Downstream dependencies")
    upstream_callers: List[str] = Field(default_factory=list, description="Upstream callers")
    
    blast_radius_summary: str = Field("", description="Summary of the blast radius")
    affected_files: List[str] = Field(default_factory=list, description="Affected files")
    affected_apis: List[str] = Field(default_factory=list, description="Affected APIs")
    
    migration_plan: List[str] = Field(default_factory=list, description="Migration plan steps")
    testing_checklist: List[str] = Field(default_factory=list, description="Testing checklist")
    engineering_actions: List[str] = Field(default_factory=list, description="Engineering actions")
