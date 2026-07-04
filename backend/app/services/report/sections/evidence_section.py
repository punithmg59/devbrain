from typing import Optional
from app.services.intent.schemas import Intent
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.report.schemas.engineering_report import ReportSectionModel
from .base_section import BaseSection


class EvidenceSection(BaseSection):
    @property
    def section_type(self) -> str:
        return "evidence"

    @property
    def priority(self) -> int:
        return 30

    def build(self, intent: Intent, decision: EngineeringDecision) -> Optional[ReportSectionModel]:
        return ReportSectionModel(
            type=self.section_type,
            title="Engineering Evidence",
            priority=self.priority,
            content={
                "reasoning": decision.primary_reason
            }
        )
