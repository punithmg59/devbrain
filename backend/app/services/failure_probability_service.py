"""Estimate failure and degradation probabilities from graph metrics."""

from __future__ import annotations


class FailureProbabilityService:
    def estimate(
        self,
        risk_score: float,
        blast_radius_score: float,
        critical_paths: int,
        centrality: float,
        workflow_reach: int,
        api_count: int,
    ) -> int:
        raw = 0.0
        raw += min(1.0, risk_score) * 0.35
        raw += min(1.0, blast_radius_score / 100.0) * 0.25
        raw += min(1.0, centrality / 100.0) * 0.2
        raw += min(1.0, critical_paths / 3.0) * 0.12
        raw += min(1.0, workflow_reach / 5.0) * 0.08
        raw += min(1.0, api_count / 10.0) * 0.05
        probability = int(min(100.0, max(0.0, raw * 100)))
        if critical_paths >= 2:
            probability = min(100, probability + 8)
        return probability

    def degradation_probability(self, failure_probability: int, risk_score: float) -> int:
        degrade = int(min(100.0, max(0.0, failure_probability * 0.7 + risk_score * 20)))
        return max(0, min(100, degrade))
