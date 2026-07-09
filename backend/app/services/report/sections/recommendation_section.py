from typing import Optional
from app.services.intent.schemas import Intent
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.engineering_evidence.models import EngineeringEvidence
from app.services.report.schemas.engineering_report import ReportSectionModel
from .base_section import BaseSection


class RecommendationSection(BaseSection):
    @property
    def section_type(self) -> str:
        return "recommendations"

    @property
    def priority(self) -> int:
        return 40

    def build(self, intent: Intent, decision: EngineeringDecision, evidence: Optional[EngineeringEvidence] = None) -> Optional[ReportSectionModel]:
        if not decision.recommended_actions and not decision.alternative_options:
            return None
            
        return ReportSectionModel(
            type=self.section_type,
            title="Recommendations",
            priority=self.priority,
            content={
                "actions": decision.recommended_actions,
                "alternatives": decision.alternative_options,
            }
        )
