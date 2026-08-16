"""
models/semantic.py
-------------------
Phase 4.3 — Language-Independent Semantic Extraction Data Models.

Defines production-quality, type-safe Pydantic V2 models representing structured
semantic entities extracted from source files (modules, classes, functions,
variables, imports, parameters, decorators).

Design Principles
-----------------
- **Language-Independent**: Models are generic across Python, TypeScript, Java,
  Go, C#.
- **Zero Parser/Engine Dependencies**: Pure data contracts dependent only on
  `NodeRange` (from models.ast). Does NOT import Tree-sitter.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (`model_dump()`, `model_dump_json()`).
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.ast import NodeRange


class ParameterKind(str, Enum):
    """Classification of function/method parameter passing modes."""
    POSITIONAL_ONLY = "positional_only"
    POSITIONAL = "positional"
    KEYWORD = "keyword"
    KEYWORD_ONLY = "keyword_only"
    VAR_POSITIONAL = "var_positional"  # *args
    VAR_KEYWORD = "var_keyword"        # **kwargs


class VariableScope(str, Enum):
    """Scope classification of extracted variables."""
    GLOBAL = "global"
    LOCAL = "local"
    CLASS_ATTRIBUTE = "class_attribute"


class MethodModifier(str, Enum):
    """Special behavioral and access modifiers for methods."""
    INSTANCE = "instance"
    STATIC = "static"
    CLASS = "class"
    PROPERTY = "property"
    ABSTRACT = "abstract"


class ExtractedDecorator(BaseModel):
    """Structured representation of a decorator / annotation expression."""
    expression: str = Field(..., description="Full decorator expression, e.g. '@app.get(\"/users\")'")
    name: str = Field(..., description="Base identifier or attribute path, e.g. 'app.get'")
    arguments: List[str] = Field(default_factory=list, description="Raw argument expressions if callable decorator")
    range: Optional[NodeRange] = Field(default=None, description="Source code range")


class ExtractedParameter(BaseModel):
    """Function or method parameter specification."""
    name: str = Field(..., description="Parameter identifier name")
    annotation: Optional[str] = Field(default=None, description="Type annotation string as written")
    has_default: bool = Field(default=False, description="True if a default value is specified")
    default_value: Optional[str] = Field(default=None, description="Literal representation of default value")
    kind: ParameterKind = Field(default=ParameterKind.POSITIONAL, description="Parameter passing classification")


class ExtractedImport(BaseModel):
    """Import statement specification."""
    module: Optional[str] = Field(default=None, description="Imported module path, e.g. 'os.path'")
    imported_names: List[str] = Field(default_factory=list, description="Specific imported symbols, e.g. ['Path', 'join']")
    aliases: Dict[str, str] = Field(default_factory=dict, description="Symbol to alias map, e.g. {'Path': 'P'}")
    is_relative: bool = Field(default=False, description="True if relative import, e.g. 'from . import foo'")
    relative_level: int = Field(default=0, ge=0, description="Number of leading dots in relative import")
    range: Optional[NodeRange] = Field(default=None, description="Source location range")


class ExtractedVariable(BaseModel):
    """Global, local, or class attribute variable declaration."""
    name: str = Field(..., description="Variable identifier name")
    scope: VariableScope = Field(..., description="Scope level (global, local, class_attribute)")
    annotation: Optional[str] = Field(default=None, description="Type annotation string as written")
    inferred_expression_kind: str = Field(
        default="unknown",
        description="Syntactic kind of assigned expression ('literal', 'call', 'binary_op', 'identifier', 'unknown')"
    )
    is_constant: bool = Field(default=False, description="True if name follows uppercase constant naming convention")
    value_snippet: Optional[str] = Field(default=None, description="Source code value snippet if available")
    range: Optional[NodeRange] = Field(default=None, description="Source location range")


class ExtractedFunction(BaseModel):
    """Function or method definition entity."""
    name: str = Field(..., description="Function symbol name (or '<lambda>')")
    is_async: bool = Field(default=False, description="True if async definition")
    decorators: List[ExtractedDecorator] = Field(default_factory=list, description="Decorators applied to function")
    parameters: List[ExtractedParameter] = Field(default_factory=list, description="Function parameters list")
    return_annotation: Optional[str] = Field(default=None, description="Return type annotation string as written")
    docstring: Optional[str] = Field(default=None, description="Extracted docstring text")
    range: Optional[NodeRange] = Field(default=None, description="Source code location range")
    nesting_level: int = Field(default=0, ge=0, description="Lexical nesting depth (0 = top-level module function)")
    enclosing_class: Optional[str] = Field(default=None, description="Enclosing class name if a method")
    enclosing_function: Optional[str] = Field(default=None, description="Enclosing function name if nested function")
    method_modifiers: List[MethodModifier] = Field(default_factory=list, description="Method modifiers (instance, static, class, property, abstract)")
    is_generator: bool = Field(default=False, description="True if function contains yield / yield from statements")
    local_variables: List[ExtractedVariable] = Field(default_factory=list, description="Local variables defined in function body")
    http_method: Optional[str] = Field(default=None, description="HTTP method if this is an API route (GET, POST, PUT, DELETE, etc.)")
    route_path: Optional[str] = Field(default=None, description="Route path if this is an API route (e.g., '/users/{id}')")


class ExtractedClass(BaseModel):
    """Class definition entity."""
    name: str = Field(..., description="Class symbol name")
    docstring: Optional[str] = Field(default=None, description="Extracted docstring text")
    decorators: List[ExtractedDecorator] = Field(default_factory=list, description="Decorators applied to class")
    base_classes: List[str] = Field(default_factory=list, description="Base class names / expressions inherited")
    range: Optional[NodeRange] = Field(default=None, description="Source code location range")
    nesting_level: int = Field(default=0, ge=0, description="Lexical nesting depth (0 = top-level class)")
    parent_class: Optional[str] = Field(default=None, description="Enclosing class name if nested class")
    methods: List[ExtractedFunction] = Field(default_factory=list, description="Methods defined within class")
    class_attributes: List[ExtractedVariable] = Field(default_factory=list, description="Class attributes defined within class body")


class ExtractedModule(BaseModel):
    """Module-level entity container for a single parsed source file."""
    name: str = Field(..., description="Module name (derived from file path or file name)")
    file_path: str = Field(..., description="Source file relative path")
    docstring: Optional[str] = Field(default=None, description="Module-level docstring")
    imports: List[ExtractedImport] = Field(default_factory=list, description="Import statements in module")
    classes: List[ExtractedClass] = Field(default_factory=list, description="Classes defined in module")
    functions: List[ExtractedFunction] = Field(default_factory=list, description="Top-level functions in module")
    global_variables: List[ExtractedVariable] = Field(default_factory=list, description="Global variables defined in module")
    constants: List[ExtractedVariable] = Field(default_factory=list, description="Global constants (UPPER_CASE naming convention)")


class SemanticMetrics(BaseModel):
    """Performance and telemetry metrics captured during semantic extraction."""
    extraction_duration_ms: float = Field(default=0.0, ge=0.0, description="Extraction duration in milliseconds")
    module_count: int = Field(default=1, ge=0, description="Total modules extracted")
    class_count: int = Field(default=0, ge=0, description="Total classes extracted")
    function_count: int = Field(default=0, ge=0, description="Total functions/methods extracted")
    import_count: int = Field(default=0, ge=0, description="Total import statements extracted")
    variable_count: int = Field(default=0, ge=0, description="Total variables extracted")
    constant_count: int = Field(default=0, ge=0, description="Total constants extracted")
    memory_rss_bytes: int = Field(default=0, ge=0, description="Peak memory usage during extraction in bytes")


class SemanticExtractionResult(BaseModel):
    """Canonical output container for single-file semantic extraction."""
    result_id: str = Field(
        default_factory=lambda: f"sem-{uuid.uuid4().hex[:12]}",
        description="Globally unique semantic extraction result identifier",
    )
    file_path: str = Field(..., description="Source file path")
    language: str = Field(default="python", description="Programming language")
    module: ExtractedModule = Field(..., description="Structured extracted module tree")
    metrics: SemanticMetrics = Field(default_factory=SemanticMetrics, description="Extraction metrics and telemetry")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings during extraction")
    errors: List[str] = Field(default_factory=list, description="Non-fatal error records during extraction")
