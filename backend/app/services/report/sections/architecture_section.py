from typing import Optional
from app.services.intent.schemas import Intent
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.engineering_evidence.models import EngineeringEvidence
from app.services.report.schemas.engineering_report import ReportSectionModel
from .base_section import BaseSection


class ArchitectureSection(BaseSection):
    @property
    def section_type(self) -> str:
        return "architecture"

    @property
    def priority(self) -> int:
        return 15

    def build(self, intent: Intent, decision: EngineeringDecision, evidence: Optional[EngineeringEvidence] = None) -> Optional[ReportSectionModel]:
        return ReportSectionModel(
            type=self.section_type,
            title="Architecture Overview",
            priority=self.priority,
            content={
                "components": decision.affected_components
            }
        )
