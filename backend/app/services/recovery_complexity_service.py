"""Recovery complexity estimation for change simulations."""

from __future__ import annotations


class RecoveryComplexityService:
    def estimate(
        self,
        dependency_count: int,
        critical_path_count: int,
        workflow_reach: int,
        service_count: int,
    ) -> str:
        score = 0
        score += min(5, dependency_count // 4)
        score += min(5, critical_path_count * 2)
        score += min(4, workflow_reach)
        score += min(3, service_count)

        if score >= 12:
            return "CRITICAL"
        if score >= 9:
            return "HIGH"
        if score >= 6:
            return "MEDIUM"
        return "LOW"
