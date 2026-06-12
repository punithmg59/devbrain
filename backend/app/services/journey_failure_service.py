"""Journey impact assessment for change simulations."""

from __future__ import annotations

from typing import Iterable

from app.services.failure_classifier import FailureClassifier


class JourneyFailureService:
    def __init__(self) -> None:
        self.classifier = FailureClassifier()

    def assess_journeys(
        self,
        journeys: Iterable[str],
        impacted_workflow_count: int,
        failure_probability: int,
    ) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for journey in sorted(set(journeys)):
            severity = self.classifier.classify_journey(failure_probability, impacted_workflow_count)
            out.append(
                {
                    "journey_name": journey,
                    "severity": severity,
                    "reason": f"Journey touches {impacted_workflow_count} workflow(s) and probability {failure_probability}%.",
                }
            )
        return out
