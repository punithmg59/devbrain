"""
AuthenticationProvider abstract interface and LocalAuthenticationProvider implementation.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Optional

from graph_storage.exceptions import GraphStorageError
from graph_storage.security.principal import Principal


class AuthenticationProvider(ABC):
    """Abstract interface for identity verification and principal authentication."""

    @abstractmethod
    def authenticate(self, credentials: Dict[str, str]) -> Principal:
        """Authenticate user credentials and return a Principal."""
        ...

    @abstractmethod
    def validate_identity(self, principal: Principal) -> bool:
        """Validate whether a principal identity remains active and valid."""
        ...

    @abstractmethod
    def refresh(self, principal: Principal) -> Principal:
        """Refresh principal session and timestamps."""
        ...

    @abstractmethod
    def logout(self, principal: Principal) -> bool:
        """Invalidate principal session."""
        ...


class LocalAuthenticationProvider(AuthenticationProvider):
    """Default local in-memory authentication provider."""

    def __init__(self):
        self._user_db: Dict[str, str] = {"admin": "admin_pass", "user": "user_pass"}
        self._active_principals: Dict[str, Principal] = {}

    def register_user(self, username: str, password: str) -> None:
        self._user_db[username] = password

    def authenticate(self, credentials: Dict[str, str]) -> Principal:
        username = credentials.get("username")
        password = credentials.get("password")
        if not username or not password:
            raise GraphStorageError("Username and password credentials are required")

        stored_pass = self._user_db.get(username)
        if stored_pass is None or stored_pass != password:
            raise GraphStorageError(f"Authentication failed for user '{username}'")

        roles = ["admin"] if username == "admin" else ["user"]
        permissions = ["*"] if username == "admin" else ["read", "write"]

        principal = Principal(
            principal_id=f"p_{username}",
            username=username,
            roles=roles,
            permissions=permissions,
            authenticated_time=time.time(),
        )
        self._active_principals[principal.principal_id] = principal
        return principal

    def validate_identity(self, principal: Principal) -> bool:
        return principal.principal_id in self._active_principals

    def refresh(self, principal: Principal) -> Principal:
        if not self.validate_identity(principal):
            raise GraphStorageError("Cannot refresh invalid or logged out principal")
        refreshed = Principal(
            principal_id=principal.principal_id,
            username=principal.username,
            roles=principal.roles,
            permissions=principal.permissions,
            metadata=principal.metadata,
            authenticated_time=time.time(),
        )
        self._active_principals[principal.principal_id] = refreshed
        return refreshed

    def logout(self, principal: Principal) -> bool:
        return self._active_principals.pop(principal.principal_id, None) is not None
