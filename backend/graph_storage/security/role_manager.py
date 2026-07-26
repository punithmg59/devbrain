"""
Role model definition and RoleManager implementation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from graph_storage.exceptions import GraphStorageError
from graph_storage.security.permission_model import PermissionModel


@dataclass(frozen=True)
class Role:
    """Immutable role definition containing permission assignments."""

    role_id: str
    name: str
    permissions: List[PermissionModel] = field(default_factory=list)
    description: str = ""


class RoleManager:
    """Manager for creating roles, assigning permissions, and validating role memberships."""

    def __init__(self):
        self._roles: Dict[str, Role] = {}
        # Seed built-in roles
        self.create_role(
            "admin",
            "Administrator",
            [PermissionModel("p_admin", "*", "*")],
            "Full storage administrative access",
        )
        self.create_role(
            "user",
            "Standard User",
            [PermissionModel("p_read", "*", "read"), PermissionModel("p_write", "*", "write")],
            "Standard read/write access",
        )

    def create_role(
        self, role_id: str, name: str, permissions: List[PermissionModel], description: str = ""
    ) -> Role:
        role = Role(role_id=role_id, name=name, permissions=permissions, description=description)
        self._roles[role_id] = role
        return role

    def get_role(self, role_id: str) -> Optional[Role]:
        return self._roles.get(role_id)

    def permissions_for_roles(self, role_ids: List[str]) -> List[PermissionModel]:
        perms: List[PermissionModel] = []
        for rid in role_ids:
            r = self.get_role(rid)
            if r:
                perms.extend(r.permissions)
        return perms

    def validate_role(self, role_id: str) -> bool:
        return role_id in self._roles
