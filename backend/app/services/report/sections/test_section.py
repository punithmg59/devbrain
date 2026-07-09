from typing import Optional
from app.services.intent.schemas import Intent
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.engineering_evidence.models import EngineeringEvidence
from app.services.report.schemas.engineering_report import ReportSectionModel
from .base_section import BaseSection


class TestSection(BaseSection):
    @property
    def section_type(self) -> str:
        return "tests"

    @property
    def priority(self) -> int:
        return 50

    def build(self, intent: Intent, decision: EngineeringDecision, evidence: Optional[EngineeringEvidence] = None) -> Optional[ReportSectionModel]:
        if not decision.required_tests:
            return None
            
        return ReportSectionModel(
            type=self.section_type,
            title="Required Tests",
            priority=self.priority,
            content={
                "tests": decision.required_tests
            }
        )
