"""Change Simulator — adjusts traversal intent for delete/modify/refactor (deterministic)."""

from app.services.impact_engines.context import Scenario


def normalize_scenario(raw: str | None) -> Scenario:
    if raw in ("delete", "remove", "deletion"):
        return "delete"
    if raw in ("refactor", "rename", "extract"):
        return "refactor"
    return "modify"


def scenario_label(scenario: Scenario) -> str:
    return {
        "modify": "Modification",
        "delete": "Deletion",
        "refactor": "Refactoring",
    }[scenario]
