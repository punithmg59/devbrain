from typing import Optional

from app.services.intent.schemas import Intent
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.engineering_evidence.models import EngineeringEvidence
from app.services.report.schemas.engineering_report import ReportSectionModel
from .base_section import BaseSection


class PlanningSection(BaseSection):
    @property
    def section_type(self) -> str:
        return "planning"

    @property
    def priority(self) -> int:
        return 12

    def build(self, intent: Intent, decision: EngineeringDecision, evidence: Optional[EngineeringEvidence] = None) -> Optional[ReportSectionModel]:
        return ReportSectionModel(
            type=self.section_type,
            title="Implementation Strategy",
            priority=self.priority,
            content={
                "summary": decision.summary,
                "actions": decision.recommended_actions,
            },
        )
