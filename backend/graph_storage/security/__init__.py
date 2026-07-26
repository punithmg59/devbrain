"""
Security package for Graph Storage authentication, authorization, access control, and auditing.
"""

from graph_storage.security.access_policy import AccessPolicy
from graph_storage.security.access_validator import AccessValidator
from graph_storage.security.audit_logger import (
    AuditEntry,
    AuditLogger,
    AuditTrail,
)
from graph_storage.security.authentication_provider import (
    AuthenticationProvider,
    LocalAuthenticationProvider,
)
from graph_storage.security.authorization_manager import AuthorizationManager
from graph_storage.security.permission_model import PermissionModel
from graph_storage.security.principal import Principal
from graph_storage.security.resource_descriptor import ResourceDescriptor
from graph_storage.security.role_manager import Role, RoleManager
from graph_storage.security.security_events import (
    AccessValidatedEvent,
    AuditRecordedEvent,
    AuthenticationFailedEvent,
    AuthenticationSucceededEvent,
    AuthorizationDeniedEvent,
    AuthorizationGrantedEvent,
    IntegrityViolationEvent,
    PermissionCheckedEvent,
    SecurityViolationEvent,
)
from graph_storage.security.security_manager import SecurityManager
from graph_storage.security.security_metrics import SecurityMetrics
from graph_storage.security.security_policy import (
    EncryptionPolicy,
    IntegrityPolicy,
    KeyManager,
    SecurityPolicy,
)

__all__ = [
    "Principal",
    "AuthenticationProvider",
    "LocalAuthenticationProvider",
    "PermissionModel",
    "Role",
    "RoleManager",
    "ResourceDescriptor",
    "AccessPolicy",
    "AuthorizationManager",
    "AccessValidator",
    "AuditEntry",
    "AuditLogger",
    "AuditTrail",
    "IntegrityPolicy",
    "EncryptionPolicy",
    "SecurityPolicy",
    "KeyManager",
    "SecurityMetrics",
    "AuthenticationSucceededEvent",
    "AuthenticationFailedEvent",
    "AuthorizationGrantedEvent",
    "AuthorizationDeniedEvent",
    "PermissionCheckedEvent",
    "AccessValidatedEvent",
    "AuditRecordedEvent",
    "IntegrityViolationEvent",
    "SecurityViolationEvent",
    "SecurityManager",
]
