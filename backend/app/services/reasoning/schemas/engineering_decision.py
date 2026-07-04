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
    DO_NOT_DELETE = "DO_NOT_DELETE"
    SAFE_TO_DELETE = "SAFE_TO_DELETE"
    SAFE_WITH_UPDATES = "SAFE_WITH_UPDATES"
    PROCEED_WITH_CAUTION = "PROCEED_WITH_CAUTION"
    IMPLEMENT_IN_MODULE = "IMPLEMENT_IN_MODULE"
    EXPLAIN_ARCHITECTURE = "EXPLAIN_ARCHITECTURE"
    GENERATE_IMPLEMENTATION_PLAN = "GENERATE_IMPLEMENTATION_PLAN"
    REFACTOR_SAFE = "REFACTOR_SAFE"
    REFACTOR_HIGH_RISK = "REFACTOR_HIGH_RISK"
    RESOLVE_DEPENDENCY = "RESOLVE_DEPENDENCY"
    UNKNOWN = "UNKNOWN"


class EngineeringDecision(BaseModel):
    """
    The main output of the DevBrain Reasoning Engine.
    This JSON object is consumed by UI layers and the future Engineering Report layer.
    """

    decision: DecisionType = Field(..., description="The primary decision outcome")
    risk_level: RiskLevel = Field(..., description="Calculated risk severity")
    risk_score: int = Field(..., ge=0, le=100, description="Numerical risk score (0-100)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in the decision")

    summary: str = Field(..., description="A short summary of the decision")
    primary_reason: str = Field(..., description="The primary reason for this decision")

    affected_components: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Key components affected by this change (name, type, category)"
    )

    recommended_actions: List[str] = Field(
        default_factory=list,
        description="Deterministic recommendations for next steps"
    )
    alternative_options: List[str] = Field(
        default_factory=list,
        description="Alternative approaches to the proposed intent"
    )
    required_tests: List[str] = Field(
        default_factory=list,
        description="Tests that must be written or run based on the evidence"
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="Intelligent follow-up questions for the user"
    )
