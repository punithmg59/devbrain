"""
models/call_models.py
---------------------
Phase 4.7.2 — Language-Independent Function Call Detection Data Models.

Defines production-quality, type-safe Pydantic V2 data models representing
function/method/constructor/async call records, call classifications,
call metrics, validation reports, and detection results.

Design Principles
-----------------
- **Language-Independent**: Generic across Python, TypeScript, Java, Go, C#, Rust.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (`model_dump()`, `model_dump_json()`).
- **Zero AST/Parser Dependencies**: Pure data contracts dependent only on `NodeRange`.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.ast import NodeRange


class CallType(str, Enum):
    """Classification of call invocation patterns."""
    FUNCTION = "function"             # e.g. login()
    METHOD = "method"                 # e.g. user.login()
    ASYNC = "async"                   # e.g. await service.run()
    CONSTRUCTOR = "constructor"       # e.g. User()
    CLASS_METHOD = "class_method"     # e.g. User.build()
    STATIC_METHOD = "static_method"   # e.g. Math.add()
    SUPER = "super"                   # e.g. super().__init__()
    LAMBDA = "lambda"                 # e.g. func() where func = lambda x: x+1
    CALLABLE_OBJECT = "callable_object" # e.g. processor() where processor is a callable class instance
    UNKNOWN = "unknown"


class CallRecord(BaseModel):
    """
    Canonical representation of an individual function, method, constructor,
    or indirect call invocation occurrence.
    """
    call_id: str = Field(
        default_factory=lambda: f"call-{uuid.uuid4().hex[:12]}",
        description="Unique call occurrence identifier",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    caller_symbol_id: Optional[str] = Field(
        default=None,
        description="Bound symbol ID of the enclosing caller function/method/module",
    )
    caller_fqn: Optional[str] = Field(
        default=None,
        description="FQN of the enclosing caller function/method/module",
    )
    callee_symbol_id: Optional[str] = Field(
        default=None,
        description="Bound target callee symbol ID in SymbolTable after resolution",
    )
    callee_fqn: Optional[str] = Field(
        default=None,
        description="Resolved FQN of target callee symbol, e.g. 'fastapi.applications.FastAPI'",
    )
    callee_name: Optional[str] = Field(
        default=None,
        description="Raw callee expression string as written in source code, e.g. 'FastAPI', 'user.login'",
    )
    file_path: str = Field(..., description="Source file path relative to repository root")
    line: int = Field(..., ge=1, description="1-indexed start line number")
    column: int = Field(..., ge=0, description="0-indexed start column offset")
    end_line: Optional[int] = Field(default=None, ge=1, description="1-indexed end line number")
    end_column: Optional[int] = Field(default=None, ge=0, description="0-indexed end column offset")
    call_type: CallType = Field(default=CallType.UNKNOWN, description="Call classification kind")
    is_async: bool = Field(default=False, description="True if async / awaited call")
    is_constructor: bool = Field(default=False, description="True if class instantiation constructor call")
    is_method: bool = Field(default=False, description="True if method invocation on an object instance")
    is_classmethod: bool = Field(default=False, description="True if classmethod invocation")
    is_staticmethod: bool = Field(default=False, description="True if staticmethod invocation")
    is_super_call: bool = Field(default=False, description="True if super() invocation")
    is_lambda: bool = Field(default=False, description="True if lambda function invocation")
    is_external: bool = Field(default=False, description="True if callee is stdlib or third-party package")
    arguments: List[str] = Field(default_factory=list, description="Positional argument expressions")
    keyword_arguments: Dict[str, str] = Field(default_factory=dict, description="Keyword argument name -> expression map")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Resolution confidence score (0.0 to 1.0)")
    range: Optional[NodeRange] = Field(default=None, description="Source location range")


class CallMetrics(BaseModel):
    """Performance telemetry and distribution metrics for call detection."""
    total_calls: int = Field(default=0, ge=0, description="Total call invocation expressions detected")
    resolved_calls: int = Field(default=0, ge=0, description="Total calls resolved to target callee Symbol IDs")
    unresolved_calls: int = Field(default=0, ge=0, description="Total calls that could not be resolved to Symbol IDs")
    method_calls: int = Field(default=0, ge=0, description="Total method calls detected")
    constructor_calls: int = Field(default=0, ge=0, description="Total constructor calls detected")
    async_calls: int = Field(default=0, ge=0, description="Total async calls detected")
    lambda_calls: int = Field(default=0, ge=0, description="Total lambda calls detected")
    external_calls: int = Field(default=0, ge=0, description="Total calls to external / stdlib functions")
    average_lookup_time_us: float = Field(default=0.0, ge=0.0, description="Average index query latency in microseconds")
    build_duration_ms: float = Field(default=0.0, ge=0.0, description="Call detection build duration in milliseconds")
    memory_bytes: int = Field(default=0, ge=0, description="Estimated memory usage in bytes")


class CallValidationIssue(BaseModel):
    """Individual issue recorded during call graph integrity validation."""
    severity: str = Field(..., description="'error' or 'warning'")
    code: str = Field(..., description="Issue code, e.g. 'DUPLICATE_CALL', 'DANGLING_CALLEE_ID'")
    message: str = Field(..., description="Human-readable issue explanation")
    call_id: Optional[str] = Field(default=None, description="Associated call ID if applicable")
    file_path: Optional[str] = Field(default=None, description="Source file path where issue occurred")


class CallValidationReport(BaseModel):
    """Structured validation report for function call detection."""
    is_valid: bool = Field(default=True, description="True if no errors were found")
    issues: List[CallValidationIssue] = Field(default_factory=list, description="Validation issues list")
    error_count: int = Field(default=0, ge=0, description="Total error count")
    warning_count: int = Field(default=0, ge=0, description="Total warning count")


class FunctionCallDetectionResult(BaseModel):
    """Output container for the function call detection stage execution."""
    result_id: str = Field(
        default_factory=lambda: f"calldet-{uuid.uuid4().hex[:12]}",
        description="Unique call detection result ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    calls: Dict[str, CallRecord] = Field(
        default_factory=dict,
        description="Map of call_id -> CallRecord object",
    )
    metrics: CallMetrics = Field(default_factory=CallMetrics, description="Call detection metrics and performance stats")
    validation_report: CallValidationReport = Field(
        default_factory=CallValidationReport,
        description="Validation report for call detection",
    )
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings recorded during call detection")
    errors: List[str] = Field(default_factory=list, description="Non-fatal error records during call detection")
