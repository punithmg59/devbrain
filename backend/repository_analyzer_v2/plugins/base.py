import re
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from models import Edge, Import, Node, RepositoryFile, Symbol


class PluginMetadata(BaseModel):
    """Metadata describing a repository analyzer plugin."""
    name: str = Field(..., description="Name of the plugin (e.g., 'PythonAnalyzer')")
    version: str = Field(..., description="Semantic version of the plugin (e.g., '1.0.0')")
    description: str = Field(..., description="Brief description of what the plugin does")
    capabilities: List[str] = Field(
        default_factory=list, 
        description="List of capability flags (e.g., ['symbols', 'imports', 'calls', 'routes'])"
    )

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Ensure version matches standard semantic versioning loosely."""
        if not re.match(r"^\d+\.\d+\.\d+", v):
            raise ValueError("Version must follow semantic versioning (e.g., X.Y.Z)")
        return v


class AnalyzerPlugin(ABC):
    """
    Abstract base class for all language-specific analyzer plugins.
    Defines the contract that every plugin must fulfill to integrate into the pipeline.
    """
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Returns the plugin metadata including version and capabilities."""
        pass
        
    @abstractmethod
    def initialize(self, config: Any) -> None:
        """
        Initialize the plugin with necessary configuration.
        This may include setting up parsers, loading rules, or allocating resources.
        """
        pass
        
    @abstractmethod
    def language(self) -> str:
        """
        Return the primary programming language this plugin supports.
        Must match one of the system's supported languages (e.g., 'python', 'typescript').
        """
        pass
        
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """
        Return a list of file extensions supported by this plugin (without leading dots).
        Example: ['py', 'pyi']
        """
        pass
        
    @abstractmethod
    def parse(self, file: RepositoryFile) -> Any:
        """
        Parse the source file and return an Abstract Syntax Tree (AST) 
        or an Intermediate Representation (IR).
        """
        pass
        
    @abstractmethod
    def extract_entities(self, file: RepositoryFile, ast: Any) -> List[Node]:
        """
        Extract core architectural entities (like modules, classes, interfaces) from the AST.
        """
        pass
        
    @abstractmethod
    def extract_symbols(self, file: RepositoryFile, ast: Any) -> List[Symbol]:
        """
        Extract defined symbols (functions, variables, properties) from the AST.
        """
        pass
        
    @abstractmethod
    def extract_imports(self, file: RepositoryFile, ast: Any) -> List[Import]:
        """
        Extract import statements or module dependencies from the AST.
        """
        pass
        
    @abstractmethod
    def extract_calls(self, file: RepositoryFile, ast: Any) -> List[Edge]:
        """
        Extract function, method, or class instantiations that represent dependencies.
        Returns Edge objects linking the source file/node to the target.
        """
        pass
        
    @abstractmethod
    def extract_routes(self, file: RepositoryFile, ast: Any) -> List[Any]:
        """
        Extract API routes or web endpoints if applicable to the language/framework.
        Returns a list of Route objects or dictionaries.
        """
        pass
        
    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up any resources used by the plugin, such as open file handles or subprocesses.
        """
        pass
