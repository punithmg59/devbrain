from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PipelineStage(str, Enum):
    """Enumeration of pipeline stages for the analysis run."""
    DISCOVERY = "discovery"
    PARSING = "parsing"
    EXTRACTION = "extraction"
    LINKING = "linking"
    VALIDATION = "validation"
    REPORTING = "reporting"


class AnalysisResult(BaseModel):
    """Represents the output summary of an analysis run."""
    repository_id: str = Field(..., description="The repository that was analyzed")
    total_files_analyzed: int = Field(default=0, ge=0, description="Total number of files processed")
    total_nodes: int = Field(default=0, ge=0, description="Total nodes generated in the graph")
    total_edges: int = Field(default=0, ge=0, description="Total edges generated in the graph")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered during analysis")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metrics or results data")


class AnalysisRun(BaseModel):
    """Represents an execution of the repository analyzer pipeline."""
    id: str = Field(..., description="Unique run identifier")
    repository_id: str = Field(..., description="The repository being analyzed")
    status: str = Field(default="pending", description="Current status (e.g., 'pending', 'running', 'completed', 'failed')")
    current_stage: Optional[PipelineStage] = Field(default=None, description="The stage the pipeline is currently in")
    
    started_at: datetime = Field(default_factory=datetime.utcnow, description="When the run was initiated")
    completed_at: Optional[datetime] = Field(default=None, description="When the run completed or failed")
    
    result: Optional[AnalysisResult] = Field(default=None, description="The final result summary of the analysis")
