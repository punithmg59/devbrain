"""
AuthorizationManager implementation evaluating permissions and access rules.
"""

from typing import List, Optional

from graph_storage.exceptions import GraphStorageError
from graph_storage.security.principal import Principal
from graph_storage.security.resource_descriptor import ResourceDescriptor
from graph_storage.security.role_manager import RoleManager


class AuthorizationManager:
    """Manager evaluating principal roles and permissions against requested resources and operations."""

    def __init__(self, role_manager: Optional[RoleManager] = None):
        self.role_manager = role_manager or RoleManager()

    def check_permission(self, principal: Principal, resource_type: str, operation: str) -> bool:
        """Check if principal has permission for resource_type and operation."""
        if "*" in principal.permissions:
            return True

        # Check direct principal permissions
        if operation in principal.permissions or f"{resource_type}:{operation}" in principal.permissions:
            return True

        # Check permissions from assigned roles
        role_perms = self.role_manager.permissions_for_roles(principal.roles)
        for perm in role_perms:
            if perm.resource in ("*", resource_type) and perm.operation in ("*", operation):
                return True

        return False

    def authorize(self, principal: Principal, resource: ResourceDescriptor, operation: str) -> bool:
        """Authorize principal access to a target resource descriptor."""
        return self.check_permission(principal, resource.resource_type, operation)

    def evaluate(self, principal: Principal, resource: ResourceDescriptor, operation: str) -> bool:
        """Evaluate access authorization rule."""
        return self.authorize(principal, resource, operation)
