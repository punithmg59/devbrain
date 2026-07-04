from typing import Optional
from app.services.intent.schemas import Intent
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.report.schemas.engineering_report import ReportSectionModel
from .base_section import BaseSection


class SummarySection(BaseSection):
    @property
    def section_type(self) -> str:
        return "summary"

    @property
    def priority(self) -> int:
        return 10

    def build(self, intent: Intent, decision: EngineeringDecision) -> Optional[ReportSectionModel]:
        return ReportSectionModel(
            type=self.section_type,
            title="Decision Summary",
            priority=self.priority,
            content={
                "summary": decision.summary,
                "reasoning": decision.primary_reason,
            }
        )
