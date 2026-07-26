"""
AuditEntry, AuditLogger, and AuditTrail implementation.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit trail record."""

    timestamp: float
    principal_id: str
    resource: str
    action: str
    result: str  # "GRANTED", "DENIED", "AUTHENTICATED", "FAILED"
    reason: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)


class AuditLogger:
    """Append-only audit logger for security accountability."""

    def __init__(self):
        self._entries: List[AuditEntry] = []
        self._lock = threading.RLock()

    def log_access(
        self, principal_id: str, resource: str, action: str, result: str, reason: str = "", metadata: Dict[str, str] = None
    ) -> AuditEntry:
        """Log an access attempt or security event."""
        entry = AuditEntry(
            timestamp=time.time(),
            principal_id=principal_id,
            resource=resource,
            action=action,
            result=result,
            reason=reason,
            metadata=metadata or {},
        )
        with self._lock:
            self._entries.append(entry)
        return entry

    def log_failure(self, principal_id: str, resource: str, action: str, reason: str) -> AuditEntry:
        return self.log_access(principal_id, resource, action, "DENIED", reason)

    def export(self) -> List[AuditEntry]:
        with self._lock:
            return list(self._entries)


class AuditTrail:
    """Query service for searching and filtering audit log history."""

    def __init__(self, logger: AuditLogger):
        self.logger = logger

    def history(self, limit: int = 100) -> List[AuditEntry]:
        entries = self.logger.export()
        return entries[-limit:]

    def search_by_principal(self, principal_id: str) -> List[AuditEntry]:
        return [e for e in self.logger.export() if e.principal_id == principal_id]

    def search_by_result(self, result: str) -> List[AuditEntry]:
        return [e for e in self.logger.export() if e.result == result]
