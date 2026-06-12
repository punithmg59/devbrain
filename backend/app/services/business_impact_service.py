"""Business impact from user journeys — deterministic."""

from __future__ import annotations

JOURNEY_BUSINESS_MAP: dict[str, dict] = {
    "user_login": {
        "category": "Authentication",
        "impact_label": "Authentication Failure",
        "reason": "Core authentication workflow affected — users may be unable to sign in.",
    },
    "repo_onboarding": {
        "category": "Activation",
        "impact_label": "Onboarding Disruption",
        "reason": "Repository onboarding journey affected — new user activation may stall.",
    },
    "engineering_intelligence": {
        "category": "Core Product Value",
        "impact_label": "Intelligence Degradation",
        "reason": "Engineering intelligence journey affected — analysis and impact features may fail.",
    },
    "dashboard_access": {
        "category": "User Experience",
        "impact_label": "Dashboard Reliability",
        "reason": "Dashboard access journey affected — logged-in users may see errors.",
    },
}


class BusinessImpactService:
    def analyze(self, journey_impacts: list[dict]) -> list[dict]:
        out: list[dict] = []
        seen: set[str] = set()
        for ji in journey_impacts:
            jid = ji.get("journey_id", "")
            meta = JOURNEY_BUSINESS_MAP.get(jid)
            if not meta or meta["category"] in seen:
                continue
            seen.add(meta["category"])
            out.append(
                {
                    "category": meta["category"],
                    "impact_label": meta["impact_label"],
                    "severity": ji.get("severity", "medium"),
                    "journey_name": ji.get("journey_name"),
                    "reason": meta["reason"],
                }
            )
        return out

    def summary_lines(self, business_impacts: list[dict]) -> list[str]:
        return [
            f"{b['impact_label']} ({b['severity'].upper()}): {b['reason']}"
            for b in business_impacts
        ]
