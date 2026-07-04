from typing import Optional

from app.services.intent.schemas import Intent
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.report.schemas.engineering_report import ReportSectionModel
from .base_section import BaseSection


class HeroSection(BaseSection):
    @property
    def section_type(self) -> str:
        return "hero"

    @property
    def priority(self) -> int:
        return 0

    def build(self, intent: Intent, decision: EngineeringDecision) -> Optional[ReportSectionModel]:
        return ReportSectionModel(
            type=self.section_type,
            title="Engineering Overview",
            priority=self.priority,
            content={
                "verdict": decision.summary,
                "risk_level": decision.risk_level.value,
                "risk_score": decision.risk_score,
                "confidence": decision.confidence,
            },
        )
