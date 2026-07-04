"""
Intent Schema Definitions

Defines strongly typed objects for the Intent Engine.
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class IntentType(str, Enum):
    """Supported intent types for engineering questions."""
    
    EXPLAIN = "EXPLAIN"
    DELETE = "DELETE"
    RENAME = "RENAME"
    REFACTOR = "REFACTOR"
    ADD_FEATURE = "ADD_FEATURE"
    DEPENDENCY = "DEPENDENCY"
    ARCHITECTURE = "ARCHITECTURE"
    PLANNING = "PLANNING"
    UNKNOWN = "UNKNOWN"


class TargetType(str, Enum):
    """Supported target types for engineering questions."""
    
    REPOSITORY = "repository"
    FOLDER = "folder"
    FILE = "file"
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    SERVICE = "service"
    API = "api"
    DATABASE_TABLE = "database_table"
    WORKFLOW = "workflow"
    MODULE = "module"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class ExtractedEntity(BaseModel):
    """Represents an entity extracted from a natural language question."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    name: str = Field(..., description="The name of the extracted entity")
    type: TargetType = Field(..., description="The type of the extracted entity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this extraction")
    start_position: int = Field(..., description="Start position in the original question")
    end_position: int = Field(..., description="End position in the original question")


class Intent(BaseModel):
    """
    Represents the classified intent from a natural language engineering question.
    
    This is the core output of the Intent Engine, providing structured information
    about what the user wants to do and what they're targeting.
    """
    
    model_config = ConfigDict(use_enum_values=True)
    
    intent: IntentType = Field(..., description="The classified intent type")
    target_type: TargetType = Field(..., description="The type of the target entity")
    target_name: str = Field(..., description="The name of the target entity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    requires_graph: bool = Field(..., description="Whether graph traversal is required")
    requires_llm: bool = Field(..., description="Whether LLM fallback is required")
    extracted_entities: List[ExtractedEntity] = Field(
        default_factory=list,
        description="All entities extracted from the question"
    )
    raw_question: str = Field(..., description="The original user question")
    normalized_question: str = Field(..., description="The normalized version of the question")
    reasoning: Optional[str] = Field(None, description="Explanation of the classification decision")


class IntentRequest(BaseModel):
    """Request model for intent classification."""
    
    repo_id: str = Field(..., description="The repository ID")
    question: str = Field(..., description="The natural language question")


class IntentResponse(BaseModel):
    """Response model for intent classification."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    intent: Intent = Field(..., description="The classified intent")
    processing_time_ms: float = Field(..., description="Time taken to classify the intent")
