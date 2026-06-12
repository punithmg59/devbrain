"""User journey definitions — deterministic, evidence-linked to workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserJourney:
    id: str
    name: str
    description: str
    workflow_names: tuple[str, ...]


USER_JOURNEYS: tuple[UserJourney, ...] = (
    UserJourney(
        id="user_login",
        name="User Login Journey",
        description="End-to-end sign-in via GitHub OAuth through session establishment.",
        workflow_names=(
            "GitHub Authentication",
            "Session Management",
        ),
    ),
    UserJourney(
        id="repo_onboarding",
        name="Repository Onboarding Journey",
        description="Connect a repository and run first analysis.",
        workflow_names=(
            "Repository Connection",
            "Repository Analysis",
        ),
    ),
    UserJourney(
        id="engineering_intelligence",
        name="Engineering Intelligence Journey",
        description="Analyze codebase and evaluate change impact.",
        workflow_names=(
            "Repository Analysis",
            "Impact Radar",
            "Code Analysis Pipeline",
        ),
    ),
    UserJourney(
        id="dashboard_access",
        name="Dashboard Access Journey",
        description="Authenticated user views repo dashboard and API data.",
        workflow_names=(
            "Session Management",
            "Dashboard Experience",
            "Public API Surface",
        ),
    ),
)


def journeys_for_workflows(workflow_names: set[str]) -> list[UserJourney]:
    out: list[UserJourney] = []
    for journey in USER_JOURNEYS:
        if any(wf in workflow_names for wf in journey.workflow_names):
            out.append(journey)
    return out


def journey_names_for_workflows(workflow_names: set[str]) -> list[str]:
    return [j.name for j in journeys_for_workflows(workflow_names)]
