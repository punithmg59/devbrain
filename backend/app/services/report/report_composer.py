from enum import Enum
from typing import Optional

from app.services.intent.schemas import Intent
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.engineering_evidence.models import EngineeringEvidence
from app.services.report.schemas.engineering_report import EngineeringReport, HeroSectionModel, ReportSectionModel
from app.services.report.section_factory import SectionFactory
from app.services.report.section_registry import SectionRegistry


class ReportComposer:
    """Transforms an EngineeringDecision into a structured EngineeringReport."""

    def __init__(
        self,
        section_registry: Optional[SectionRegistry] = None,
        section_factory: Optional[SectionFactory] = None,
    ) -> None:
        self.section_registry = section_registry or SectionRegistry()
        self.section_factory = section_factory or SectionFactory()

    def compose(
        self, 
        intent: Intent, 
        decision: EngineeringDecision,
        evidence: Optional[EngineeringEvidence] = None
    ) -> EngineeringReport:
        section_types = self.section_registry.get_section_types(intent)
        sections: list[ReportSectionModel] = []

        for section_type in section_types:
            section = self.section_factory.create(section_type)
            section_model = section.build(intent, decision, evidence)
            if section_model is not None:
                sections.append(section_model)

        hero = HeroSectionModel(
            verdict=decision.summary,
            risk_level=decision.risk_level.value,
            risk_score=decision.risk_score,
            confidence=decision.confidence,
        )

        # Use evidence validation steps if available
        next_actions = self._build_next_actions(decision, evidence)

        return EngineeringReport(
            title=self._build_title(intent),
            intent=self._enum_value(intent.intent),
            hero=hero,
            sections=sections,
            next_actions=next_actions,
            metadata={
                "source": "report_composer",
                "section_count": len(sections),
                "decision": self._enum_value(decision.decision),
                "evidence_enhanced": evidence is not None,
            },
        )

    def _build_title(self, intent: Intent) -> str:
        return f"{self._enum_value(intent.intent).replace('_', ' ').title()} Report"

    def _enum_value(self, value: object) -> str:
        if isinstance(value, Enum):
            return value.value
        return str(value)

    def _build_next_actions(
        self, 
        decision: EngineeringDecision,
        evidence: Optional[EngineeringEvidence] = None
    ) -> list[str]:
        # Prefer evidence validation steps if available
        if evidence and evidence.recommended_validation_steps:
            return list(evidence.recommended_validation_steps)
        
        if decision.recommended_actions:
            return list(decision.recommended_actions)
        if decision.follow_up_questions:
            return list(decision.follow_up_questions)
        return ["Review decision summary"]
