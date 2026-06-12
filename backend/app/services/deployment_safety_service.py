"""Deployment safety assessment for change simulations."""

from __future__ import annotations


class DeploymentSafetyService:
    def assess(self, failure_probability: int, risk_score: float, scenario: str) -> dict[str, str | list[str]]:
        if scenario == "delete" and failure_probability >= 60:
            return {
                "status": "BLOCK_DEPLOYMENT",
                "reason": "Deletion impacts critical workflows and services with high failure probability.",
                "recommendations": [
                    "Do not merge this change without replacement or rollback plan.",
                    "Seed behind a feature flag and validate in staging.",
                    "Engage the core service owner before deployment.",
                ],
            }

        if failure_probability >= 80 or risk_score >= 0.8:
            return {
                "status": "ROLLBACK_REQUIRED",
                "reason": "High failure probability and risk score indicate unsafe deployment.",
                "recommendations": [
                    "Use a canary release.",
                    "Validate all affected workflows before rollout.",
                    "Prepare rollback automation.",
                ],
            }

        if failure_probability >= 60:
            return {
                "status": "CANARY_REQUIRED",
                "reason": "Change introduces significant risk; deploy incrementally.",
                "recommendations": [
                    "Deploy to 10% traffic first.",
                    "Monitor affected APIs and user journeys.",
                ],
            }

        if failure_probability >= 35:
            return {
                "status": "FEATURE_FLAG_RECOMMENDED",
                "reason": "Moderate risk; protect rollout with feature gating.",
                "recommendations": [
                    "Keep change behind a feature flag.",
                    "Execute regression tests on impacted suites.",
                ],
            }

        return {
            "status": "SAFE_TO_DEPLOY",
            "reason": "Predicted impact is low and deployment risks are manageable.",
            "recommendations": [
                "Run standard smoke tests before promoting.",
                "Observe production metrics after deploy.",
            ],
        }
