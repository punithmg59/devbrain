"""
Natural Language Question Engine Schemas

Defines request and response models for the NLQ Engine.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class NLQRequest(BaseModel):
    """Request model for natural language question processing."""
    
    repo_id: str = Field(..., description="The repository ID")
    question: str = Field(..., description="The natural language question")


class ExtractedEntityInfo(BaseModel):
    """Information about an extracted entity."""
    
    name: str = Field(..., description="The name of the extracted entity")
    type: str = Field(..., description="The type of the extracted entity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class ResolvedEntityInfo(BaseModel):
    """Information about a resolved repository entity."""
    
    node_id: Optional[str] = Field(None, description="The resolved node ID")
    name: str = Field(..., description="The entity name")
    type: str = Field(..., description="The entity type")
    file_path: Optional[str] = Field(None, description="The file path if applicable")


class NLQResponse(BaseModel):
    """Response model for natural language question processing."""
    
    question: str = Field(..., description="The original question")
    intent: str = Field(..., description="The classified intent")
    target_type: str = Field(..., description="The type of the target entity")
    target_name: str = Field(..., description="The name of the target entity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    reasoning: Optional[str] = Field(None, description="Explanation of the classification")
    extracted_entities: List[ExtractedEntityInfo] = Field(
        default_factory=list,
        description="Entities extracted from the question"
    )
    resolved_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resolved repository entities"
    )
    answer: str = Field(..., description="The answer to the question")
    evidence: Optional[Dict[str, Any]] = Field(None, description="Supporting evidence")
    processing_time_ms: float = Field(..., description="Total processing time in milliseconds")
    requires_llm: bool = Field(..., description="Whether LLM fallback is required")
