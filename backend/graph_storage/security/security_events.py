"""
Security event model interfaces.
"""

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthenticationSucceededEvent:
    principal_id: str
    username: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class AuthenticationFailedEvent:
    username: str
    reason: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class AuthorizationGrantedEvent:
    principal_id: str
    resource: str
    operation: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class AuthorizationDeniedEvent:
    principal_id: str
    resource: str
    operation: str
    reason: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class PermissionCheckedEvent:
    principal_id: str
    permission: str
    result: bool
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class AccessValidatedEvent:
    principal_id: str
    resource_type: str
    operation: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class AuditRecordedEvent:
    principal_id: str
    action: str
    result: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class IntegrityViolationEvent:
    resource_id: str
    checksum_expected: str
    checksum_actual: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SecurityViolationEvent:
    principal_id: str
    violation_type: str
    details: str
    timestamp: float = field(default_factory=time.time)
