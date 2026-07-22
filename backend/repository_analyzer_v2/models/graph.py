from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Symbol(BaseModel):
    """Represents a code symbol (e.g., class, function, variable) within a file."""
    name: str = Field(..., description="Name of the symbol")
    kind: str = Field(..., description="Kind of symbol (e.g., 'function', 'class', 'variable')")
    line_number: Optional[int] = Field(default=None, description="Line number where the symbol is defined")


class Import(BaseModel):
    """Represents an import statement within a file."""
    source: str = Field(..., description="What is being imported (e.g., 'sys', 'MyClass')")
    module: Optional[str] = Field(default=None, description="The module imported from (e.g., 'os.path')")
    line_number: Optional[int] = Field(default=None, description="Line number of the import statement")


class Export(BaseModel):
    """Represents an exported symbol from a module."""
    name: str = Field(..., description="Name of the exported symbol")
    line_number: Optional[int] = Field(default=None, description="Line number of the export statement")


class Node(BaseModel):
    """Represents a node in the dependency graph (usually a file or module)."""
    id: str = Field(..., description="Unique identifier for the node")
    type: str = Field(..., description="Type of node (e.g., 'file', 'module', 'package')")
    name: str = Field(..., description="Human-readable name of the node")
    file_path: Optional[str] = Field(default=None, description="Relative file path if applicable")
    
    symbols: List[Symbol] = Field(default_factory=list, description="Symbols defined in this node")
    imports: List[Import] = Field(default_factory=list, description="Imports made by this node")
    exports: List[Export] = Field(default_factory=list, description="Symbols exported by this node")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional extensible metadata")


class Edge(BaseModel):
    """Represents a dependency or relationship between two nodes."""
    source_id: str = Field(..., description="Node ID of the source")
    target_id: str = Field(..., description="Node ID of the target")
    type: str = Field(..., description="Type of relationship (e.g., 'imports', 'calls', 'inherits')")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional relationship metadata")
