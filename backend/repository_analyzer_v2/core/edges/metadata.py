"""
core/edges/metadata.py
-----------------------
Reserved Namespace Metadata and Custom Attributes for DevBrain Edges.
"""

from __future__ import annotations

from typing import Any, Dict
from pydantic import BaseModel, Field


class EdgeMetadata(BaseModel):
    """
    Structured metadata container supporting reserved namespaces.
    - plugin.*
    - language.*
    - framework.*
    - graph.*
    - ai.*
    - user.*
    """
    plugin: Dict[str, Any] = Field(default_factory=dict, description="Reserved namespace plugin.*")
    language: Dict[str, Any] = Field(default_factory=dict, description="Reserved namespace language.*")
    framework: Dict[str, Any] = Field(default_factory=dict, description="Reserved namespace framework.*")
    graph: Dict[str, Any] = Field(default_factory=dict, description="Reserved namespace graph.*")
    ai: Dict[str, Any] = Field(default_factory=dict, description="Reserved namespace ai.*")
    user: Dict[str, Any] = Field(default_factory=dict, description="Reserved namespace user.*")
    custom: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary custom metadata")

    model_config = {
        "frozen": True
    }


class EdgeAttributes(BaseModel):
    """Key-value attributes container for domain-specific edge properties."""
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Domain key-value attributes")

    model_config = {
        "frozen": True
    }
