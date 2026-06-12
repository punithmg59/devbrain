"""User journey impact from workflow blast radius — deterministic."""

from __future__ import annotations

from app.services.journey_service import USER_JOURNEYS, UserJourney


class JourneyImpactService:
    def analyze(
        self,
        affected_workflow_names: set[str],
    ) -> list[dict]:
        impacts: list[dict] = []
        for journey in USER_JOURNEYS:
            overlap = [w for w in journey.workflow_names if w in affected_workflow_names]
            if not overlap:
                continue
            severity = self._severity(journey, overlap)
            impacts.append(
                {
                    "journey_id": journey.id,
                    "journey_name": journey.name,
                    "description": journey.description,
                    "severity": severity,
                    "affected_workflows": overlap,
                    "user_impact": self._user_impact_line(journey.name, severity),
                }
            )
        return impacts

    def _severity(self, journey: UserJourney, overlap: list[str]) -> str:
        if len(overlap) >= 2:
            return "high"
        if journey.id in ("user_login", "repo_onboarding"):
            return "high"
        return "medium"

    def _user_impact_line(self, journey_name: str, severity: str) -> str:
        if severity == "high":
            return f"{journey_name} is at high risk — end users may experience failures."
        return f"{journey_name} may be degraded for some users."
