"""Failure classifier for simulation severity labels."""

from __future__ import annotations


class FailureClassifier:
    def classify_probability(self, probability: float) -> str:
        if probability >= 90:
            return "CRITICAL"
        if probability >= 75:
            return "FAIL"
        if probability >= 60:
            return "HIGH_RISK"
        if probability >= 40:
            return "MEDIUM_RISK"
        if probability >= 20:
            return "LOW_RISK"
        return "SAFE"

    def classify_workflow(self, confidence: float, probability: float) -> str:
        if probability >= 85 or confidence >= 0.85:
            return "FAIL"
        if probability >= 65 or confidence >= 0.7:
            return "HIGH_RISK"
        if probability >= 45 or confidence >= 0.55:
            return "MEDIUM_RISK"
        if probability >= 25:
            return "LOW_RISK"
        return "SAFE"

    def classify_service(self, failure_probability: float, impacted_workflows: int) -> str:
        if failure_probability >= 85 and impacted_workflows >= 2:
            return "FAIL"
        if failure_probability >= 65:
            return "DEGRADED"
        if failure_probability >= 40:
            return "HIGH_RISK"
        if failure_probability >= 20:
            return "MEDIUM_RISK"
        return "SAFE"

    def classify_journey(self, failure_probability: float, workflow_count: int) -> str:
        if failure_probability >= 85 and workflow_count >= 2:
            return "FAIL"
        if failure_probability >= 60:
            return "DEGRADED"
        if failure_probability >= 40:
            return "HIGH_RISK"
        if failure_probability >= 20:
            return "MEDIUM_RISK"
        return "SAFE"
