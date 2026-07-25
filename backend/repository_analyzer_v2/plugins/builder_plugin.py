"""
plugins/builder_plugin.py
-------------------------
Step 2 — Builder Plugin Base Abstract Class.

Defines the abstract base contract for all language-specific Builder Plugins in DevBrain.
Each Builder Plugin ingests a `RepositoryWorkspace` manifest and outputs a list of
immutable `ParserResult` objects.

CRITICAL INVARIANT:
-------------------
Builder Plugins are strictly syntax-level parser orchestrators. They MUST NOT build
Symbol Tables, Graph Nodes, Edges, or persist data to PostgreSQL.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generator, List, Optional

from pydantic import BaseModel, Field

from models.parser import ParserResult
from pipeline.workspace.models import RepositoryWorkspace


class BuilderPluginCapabilities(BaseModel):
    """Capability indicators supported by a Builder Plugin."""
    syntax_ast: bool = Field(default=True, description="Produces syntactic AST root trees")
    error_recovery: bool = Field(default=True, description="Supports error recovery for malformed code")
    comments: bool = Field(default=True, description="Extracts comment nodes")
    docstrings: bool = Field(default=True, description="Extracts module, class, and function docstrings")
    type_annotations: bool = Field(default=True, description="Extracts parameter & return type annotations")


class BuilderPluginMetadata(BaseModel):
    """Metadata describing a DevBrain Builder Plugin."""
    plugin_id: str = Field(..., description="Unique plugin identifier, e.g. 'devbrain.plugin.python'")
    name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Semantic version string, e.g. '2.5.0'")
    target_language: str = Field(..., description="Primary language handled, e.g. 'python'")
    supported_extensions: List[str] = Field(default_factory=list, description="Supported extensions without leading dot")
    capabilities: BuilderPluginCapabilities = Field(default_factory=BuilderPluginCapabilities, description="Supported plugin features")


class BuilderPlugin(ABC):
    """
    Abstract Base Class for all language Builder Plugins.

    Usage::

        plugin = PythonBuilderPlugin()
        plugin.initialize()
        results = plugin.execute(workspace)
    """

    @property
    @abstractmethod
    def metadata(self) -> BuilderPluginMetadata:
        """Return plugin metadata and version specifications."""
        pass

    @property
    @abstractmethod
    def target_language(self) -> str:
        """Return primary target language handled by this plugin."""
        pass

    @abstractmethod
    def initialize(self, configuration: Optional[Dict[str, Any]] = None) -> None:
        """Initialize plugin parsers, worker thread pools, and options."""
        pass

    @abstractmethod
    def execute(self, workspace: RepositoryWorkspace) -> List[ParserResult]:
        """
        Execute batch parsing on a RepositoryWorkspace manifest.

        Parameters
        ----------
        workspace:
            Immutable `RepositoryWorkspace` manifest produced by Step 1.

        Returns
        -------
        List[ParserResult]
            List of immutable `ParserResult` objects ordered by file path.
        """
        pass

    @abstractmethod
    def execute_streaming(
        self,
        workspace: RepositoryWorkspace,
    ) -> Generator[ParserResult, None, None]:
        """
        Stream parser results iteratively for large repositories (100,000+ files).
        """
        pass
