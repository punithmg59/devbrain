"""
AccessValidator implementation verifying principal permissions across storage subsystems.
"""

from graph_storage.exceptions import GraphStorageError
from graph_storage.security.authorization_manager import AuthorizationManager
from graph_storage.security.principal import Principal
from graph_storage.security.resource_descriptor import ResourceDescriptor


class AccessValidator:
    """Validator enforcing principal access control rules across storage subsystems."""

    def __init__(self, authorization_manager: AuthorizationManager):
        self.authz_manager = authorization_manager

    def validate_access(self, principal: Principal, resource_type: str, operation: str) -> None:
        """Validate access or raise GraphStorageError."""
        resource = ResourceDescriptor(resource_id=f"res_{resource_type}", resource_type=resource_type)
        if not self.authz_manager.authorize(principal, resource, operation):
            raise GraphStorageError(
                f"Access denied: Principal '{principal.username}' is not authorized to perform '{operation}' on '{resource_type}'"
            )

    def validate_segment_access(self, principal: Principal, operation: str = "read") -> None:
        self.validate_access(principal, "segment", operation)

    def validate_snapshot_access(self, principal: Principal, operation: str = "read") -> None:
        self.validate_access(principal, "snapshot", operation)

    def validate_manifest_access(self, principal: Principal, operation: str = "read") -> None:
        self.validate_access(principal, "manifest", operation)

    def validate_partition_access(self, principal: Principal, operation: str = "read") -> None:
        self.validate_access(principal, "partition", operation)

    def validate_cache_access(self, principal: Principal, operation: str = "read") -> None:
        self.validate_access(principal, "cache", operation)

    def validate_transaction_access(self, principal: Principal, operation: str = "read") -> None:
        self.validate_access(principal, "transaction", operation)
