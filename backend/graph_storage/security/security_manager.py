"""
SecurityManager facade orchestrating authentication, authorization, access validation, and auditing.
"""

from typing import Dict, List, Optional

from graph_storage.exceptions import GraphStorageError
from graph_storage.security.access_validator import AccessValidator
from graph_storage.security.audit_logger import AuditLogger, AuditTrail
from graph_storage.security.authentication_provider import AuthenticationProvider, LocalAuthenticationProvider
from graph_storage.security.authorization_manager import AuthorizationManager
from graph_storage.security.principal import Principal
from graph_storage.security.resource_descriptor import ResourceDescriptor
from graph_storage.security.role_manager import RoleManager
from graph_storage.security.security_metrics import SecurityMetrics
from graph_storage.security.security_policy import SecurityPolicy


class SecurityManager:
    """Subsystem facade enforcing storage authentication, authorization, access control, and auditing."""

    def __init__(
        self,
        auth_provider: Optional[AuthenticationProvider] = None,
        policy: Optional[SecurityPolicy] = None,
    ):
        self.policy = policy or SecurityPolicy()
        self.auth_provider = auth_provider or LocalAuthenticationProvider()
        self.role_manager = RoleManager()
        self.authz_manager = AuthorizationManager(self.role_manager)
        self.validator = AccessValidator(self.authz_manager)
        self.audit_logger = AuditLogger()
        self.audit_trail = AuditTrail(self.audit_logger)

        # Telemetry counters
        self._auth_count = 0
        self._authz_count = 0
        self._denied_count = 0

    def authenticate(self, credentials: Dict[str, str]) -> Principal:
        """Authenticate user credentials and log audit entry."""
        self._auth_count += 1
        try:
            principal = self.auth_provider.authenticate(credentials)
            self.audit_logger.log_access(
                principal.principal_id, "authentication", "login", "AUTHENTICATED"
            )
            return principal
        except Exception as e:
            username = credentials.get("username", "unknown")
            self.audit_logger.log_failure(f"p_{username}", "authentication", "login", str(e))
            raise

    def authorize(self, principal: Principal, resource: ResourceDescriptor, operation: str) -> bool:
        """Authorize access for a principal on a resource."""
        self._authz_count += 1
        is_granted = self.authz_manager.authorize(principal, resource, operation)
        result = "GRANTED" if is_granted else "DENIED"

        if not is_granted:
            self._denied_count += 1

        self.audit_logger.log_access(
            principal.principal_id, resource.resource_type, operation, result
        )
        return is_granted

    def validate_access(self, principal: Principal, resource_type: str, operation: str) -> None:
        """Validate access or raise GraphStorageError."""
        resource = ResourceDescriptor(resource_id=f"res_{resource_type}", resource_type=resource_type)
        if not self.authorize(principal, resource, operation):
            raise GraphStorageError(
                f"Security validation failed: Principal '{principal.username}' denied '{operation}' on '{resource_type}'"
            )

    def check_permission(self, principal: Principal, resource_type: str, operation: str) -> bool:
        """Check if principal has permission."""
        return self.authz_manager.check_permission(principal, resource_type, operation)

    def audit(self) -> AuditTrail:
        """Return audit trail query service."""
        return self.audit_trail

    def security_report(self) -> SecurityMetrics:
        """Collect security metrics."""
        return SecurityMetrics(
            authentication_count=self._auth_count,
            authorization_count=self._authz_count,
            denied_requests=self._denied_count,
            audit_entries=len(self.audit_logger.export()),
            permission_checks=self._authz_count,
            security_violations=self._denied_count,
            integrity_failures=0,
        )
