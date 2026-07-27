"""
Query Versioning Models and Schema Migration Protocols.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class QueryVersion(BaseModel):
    """
    Immutable SemVer model representing the schema and AST version of an EngineeringQuery.
    """
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default="1.0.0", description="Schema version of query model")
    ast_version: str = Field(default="1.0.0", description="AST version of representation nodes")
    compatibility_version: str = Field(default="1.0.0", description="Minimum engine version required")

    def is_compatible_with(self, target_version: str) -> bool:
        """
        Verifies compatibility against a target engine schema version string.
        """
        target_major = target_version.split(".")[0]
        schema_major = self.schema_version.split(".")[0]
        return target_major == schema_major

    def __str__(self) -> str:
        return f"schema_v{self.schema_version}:ast_v{self.ast_version}"


class VersionMigrationRegistry:
    """
    Registry for registering and executing migration transformers between QueryVersions.
    """

    def __init__(self) -> None:
        self._migrations: Dict[str, Any] = {}

    def register_migration(self, from_version: str, to_version: str, transformer: Any) -> None:
        """Registers a migration transformer function."""
        key = f"{from_version}->{to_version}"
        self._migrations[key] = transformer

    def migrate(self, query_dict: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """Applies registered migrations sequentially if available."""
        key = f"{from_version}->{to_version}"
        if key in self._migrations:
            return self._migrations[key](query_dict)
        return query_dict


__all__ = [
    "QueryVersion",
    "VersionMigrationRegistry",
]
