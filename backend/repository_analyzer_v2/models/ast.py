"""
models/ast.py
-------------
Phase 3.2 — Parser-Independent Abstract Syntax Tree (AST) Data Model.

Defines DevBrain's unified AST schema (`ASTNode`, `ASTRoot`, `NodeType`,
`NodeLocation`, `NodeRange`, `NodeMetadata`, `NodeRelationship`).

Design Principles
-----------------
- **Parser-Independent**: Completely decoupled from Tree-sitter, ANTLR, or language-specific
  parser AST representation. Serves as the normalized intermediate representation (IR)
  for CodeQL, SCIP, Kythe, and static analysis graph builders.
- **Rich Navigation**: Supports bidirectional parent/child traversal, sibling references,
  definition/reference graph links, and DFS/BFS tree walking generators.
- **Exact Source Placement**: Line/column numbers and byte offsets captured via `NodeRange`.
- **Immutable Identifiers**: `node_id` and `root_id` auto-generated via UUID v4.
- **Pydantic V2 Native**: Strong validation for coordinates, non-blank strings, and recursive
  self-referential child nodes.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Semantic Node Types
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    """Normalized, parser-independent semantic AST node classifications."""
    MODULE = "module"
    PACKAGE = "package"
    FILE = "file"
    CLASS = "class"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    FUNCTION = "function"
    METHOD = "method"
    CONSTRUCTOR = "constructor"
    PARAMETER = "parameter"
    VARIABLE = "variable"
    FIELD = "field"
    PROPERTY = "property"
    IMPORT = "import"
    EXPORT = "export"
    CALL = "call"
    RETURN = "return"
    IF = "if"
    ELSE = "else"
    LOOP = "loop"
    TRY = "try"
    CATCH = "catch"
    BINARY_OP = "binary_op"
    UNARY_OP = "unary_op"
    ASSIGNMENT = "assignment"
    IDENTIFIER = "identifier"
    LITERAL = "literal"
    TYPE_ANNOTATION = "type_annotation"
    COMMENT = "comment"
    BLOCK = "block"
    EXPRESSION = "expression"
    STATEMENT = "statement"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Source Code Range Models
# ---------------------------------------------------------------------------

class NodeLocation(BaseModel):
    """Source code position coordinate (1-indexed line, 0-indexed column)."""
    line: int = Field(..., ge=1, description="1-indexed line number")
    column: int = Field(..., ge=0, description="0-indexed column offset")


class NodeRange(BaseModel):
    """Source code span specified by start and end coordinates."""
    start: NodeLocation = Field(..., description="Start location coordinate")
    end: NodeLocation = Field(..., description="End location coordinate")
    start_byte: Optional[int] = Field(default=None, ge=0, description="0-indexed start byte offset")
    end_byte: Optional[int] = Field(default=None, ge=0, description="0-indexed end byte offset")

    @model_validator(mode="after")
    def validate_range_ordering(self) -> NodeRange:
        """Validate that end location does not precede start location."""
        if self.end.line < self.start.line:
            raise ValueError(
                f"End line ({self.end.line}) cannot precede start line ({self.start.line})."
            )
        if self.end.line == self.start.line and self.end.column < self.start.column:
            raise ValueError(
                f"End column ({self.end.column}) cannot precede start column ({self.start.column}) on line {self.start.line}."
            )
        if self.start_byte is not None and self.end_byte is not None:
            if self.end_byte < self.start_byte:
                raise ValueError(
                    f"end_byte ({self.end_byte}) cannot be less than start_byte ({self.start_byte})."
                )
        return self


# ---------------------------------------------------------------------------
# Semantic Metadata & Relationships
# ---------------------------------------------------------------------------

class NodeMetadata(BaseModel):
    """Semantic metadata attributes associated with an AST node."""
    docstring: Optional[str] = Field(
        default=None,
        description="Extracted docstring or documentation comment",
    )
    modifiers: List[str] = Field(
        default_factory=list,
        description="Access and behavioral modifiers, e.g. ['public', 'async', 'static']",
    )
    decorators: List[str] = Field(
        default_factory=list,
        description="Decorators or annotations applied to node",
    )
    type_annotation: Optional[str] = Field(
        default=None,
        description="Explicit data type or return type string",
    )
    is_definition: bool = Field(
        default=False,
        description="True if node defines a new symbol",
    )
    is_reference: bool = Field(
        default=False,
        description="True if node references an existing symbol",
    )
    custom: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom key-value metadata store",
    )


class NodeRelationship(BaseModel):
    """Structural and semantic relationships connecting AST nodes across graph layers."""
    parent_id: Optional[str] = Field(
        default=None,
        description="Node ID of parent AST node",
    )
    children_ids: List[str] = Field(
        default_factory=list,
        description="List of child node IDs",
    )
    sibling_ids: List[str] = Field(
        default_factory=list,
        description="List of immediate sibling node IDs",
    )
    definition_id: Optional[str] = Field(
        default=None,
        description="ID of AST node defining the symbol (for reference nodes)",
    )
    reference_ids: List[str] = Field(
        default_factory=list,
        description="List of AST node IDs referencing this definition",
    )


# ---------------------------------------------------------------------------
# Canonical ASTNode Model
# ---------------------------------------------------------------------------

class ASTNode(BaseModel):
    """
    Parser-independent AST node representation.
    """
    node_id: str = Field(
        default_factory=lambda: f"ast-{uuid.uuid4().hex[:12]}",
        description="Globally unique AST node identifier",
    )
    type: NodeType = Field(
        ...,
        description="Semantic node classification type",
    )
    name: Optional[str] = Field(
        default=None,
        description="Symbol name or identifier string",
    )
    value: Optional[str] = Field(
        default=None,
        description="Literal string value or raw code snippet",
    )
    range: NodeRange = Field(
        ...,
        description="Source code location range",
    )
    metadata: NodeMetadata = Field(
        default_factory=NodeMetadata,
        description="Semantic metadata attributes",
    )
    relationships: NodeRelationship = Field(
        default_factory=NodeRelationship,
        description="Structural and graph relationships",
    )
    children: List[ASTNode] = Field(
        default_factory=list,
        description="Hierarchical child AST nodes",
    )

    def add_child(self, child: ASTNode) -> ASTNode:
        """
        Append a child node to this node, updating parent/child relationship links.
        """
        child.relationships.parent_id = self.node_id
        if child.node_id not in self.relationships.children_ids:
            self.relationships.children_ids.append(child.node_id)
        self.children.append(child)
        return child

    def walk(self) -> Iterator[ASTNode]:
        """
        Depth-First Search (DFS) generator yielding self and all descendant nodes.
        """
        yield self
        for child in self.children:
            yield from child.walk()

    def find_by_type(self, target_type: NodeType) -> List[ASTNode]:
        """Return all nodes in subtree matching target `NodeType`."""
        return [node for node in self.walk() if node.type == target_type]

    def find_by_name(self, name: str) -> List[ASTNode]:
        """Return all nodes in subtree matching symbol `name`."""
        return [node for node in self.walk() if node.name == name]

    def get_descendants(self) -> List[ASTNode]:
        """Return a list of all descendant nodes (excluding self)."""
        nodes = list(self.walk())
        return nodes[1:]  # Exclude self


# ---------------------------------------------------------------------------
# Canonical ASTRoot Model
# ---------------------------------------------------------------------------

class ASTRoot(BaseModel):
    """
    Root container representing the complete AST of a single source file.
    """
    root_id: str = Field(
        default_factory=lambda: f"tree-{uuid.uuid4().hex[:12]}",
        description="Globally unique AST root identifier",
    )
    file_path: str = Field(
        ...,
        min_length=1,
        description="Relative file path of the source file",
    )
    language: str = Field(
        ...,
        min_length=1,
        description="Programming language identifier",
    )
    root_node: ASTNode = Field(
        ...,
        description="Root node of the syntax tree",
    )
    total_nodes: int = Field(
        default=1,
        ge=1,
        description="Total node count in tree",
    )
    max_depth: int = Field(
        default=1,
        ge=1,
        description="Maximum depth of tree",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tree-level metadata storage",
    )

    @field_validator("file_path", "language")
    @classmethod
    def string_fields_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("String field must not be blank.")
        return v

    def walk(self) -> Iterator[ASTNode]:
        """Yield all nodes in the syntax tree via Depth-First Search."""
        yield from self.root_node.walk()

    def get_node_by_id(self, node_id: str) -> Optional[ASTNode]:
        """Find any node in the tree matching `node_id` in O(n) traversal."""
        for node in self.walk():
            if node.node_id == node_id:
                return node
        return None

    def find_nodes(self, predicate: Callable[[ASTNode], bool]) -> List[ASTNode]:
        """Return all nodes matching a custom filter predicate function."""
        return [node for node in self.walk() if predicate(node)]

    def recalculate_metrics(self) -> None:
        """
        Recalculate total_nodes and max_depth across the tree.
        """
        all_nodes = list(self.walk())
        object.__setattr__(self, "total_nodes", len(all_nodes))

        def get_depth(node: ASTNode) -> int:
            if not node.children:
                return 1
            return 1 + max(get_depth(child) for child in node.children)

        depth = get_depth(self.root_node)
        object.__setattr__(self, "max_depth", depth)
