from typing import Dict, List, Type

from app.services.intent.schemas import Intent, IntentType


class SectionRegistry:
    """Maps intents to the ordered section types that compose a report."""

    def __init__(self) -> None:
        self._registry: Dict[IntentType, List[str]] = {
            IntentType.DELETE: [
                "hero",
                "summary",
                "impact",
                "evidence",
                "recommendations",
                "tests",
                "actions",
            ],
            IntentType.EXPLAIN: ["hero", "architecture", "summary", "evidence"],
            IntentType.ARCHITECTURE: ["hero", "architecture", "impact", "evidence"],
            IntentType.PLANNING: ["hero", "planning", "recommendations", "tests", "actions"],
        }

    def get_section_types(self, intent: Intent) -> List[str]:
        return list(self._registry.get(intent.intent, ["hero", "summary", "evidence"]))
