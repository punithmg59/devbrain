from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.models.intent import Intent, TargetType


class IntentClassificationRequest(BaseModel):
    """Request schema for intent classification."""
    
    question: str = Field(..., description="The user's natural language question")
    context: Optional[dict] = Field(None, description="Optional context about the codebase")


class IntentClassificationResponse(BaseModel):
    """Response schema for intent classification."""
    
    intent: Intent = Field(..., description="The classified intent")
    target_type: Optional[TargetType] = Field(None, description="The type of target (if applicable)")
    target_name: Optional[str] = Field(None, description="The name of the target (if applicable)")
    secondary_target: Optional[str] = Field(None, description="Optional secondary target or context")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    
    original_question: str = Field(..., description="The exact question provided by the user")
    normalized_question: str = Field(..., description="The question after normalization")
    
    keywords: List[str] = Field(default_factory=list, description="Keywords extracted from the question")
    entities: Dict[str, str] = Field(default_factory=dict, description="Named entities and their mapped types")
    
    requires_graph_analysis: bool = Field(False, description="True if graph pathfinding is required")
    requires_llm: bool = Field(False, description="True if an LLM is required for fallback classification")
    requires_repository_context: bool = Field(False, description="True if repo-wide context is needed")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional pipeline data")
