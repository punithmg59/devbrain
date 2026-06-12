"""Service impact assessment for change simulations."""

from __future__ import annotations

from typing import Iterable

from app.services.failure_classifier import FailureClassifier


class ServiceFailureService:
    def __init__(self) -> None:
        self.classifier = FailureClassifier()

    def assess_services(
        self,
        services: Iterable[str],
        impacted_workflows: int,
        failure_probability: int,
    ) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for service in sorted(set(services)):
            severity = self.classifier.classify_service(failure_probability, impacted_workflows)
            out.append(
                {
                    "service_name": service,
                    "severity": severity,
                    "reason": f"Service touched by {impacted_workflows} impacted workflow(s) and probability {failure_probability}%.",
                }
            )
        return out
