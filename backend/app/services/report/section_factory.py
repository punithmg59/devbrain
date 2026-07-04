from typing import Dict, Type

from app.services.report.sections.base_section import BaseSection
from app.services.report.sections.action_section import ActionSection
from app.services.report.sections.architecture_section import ArchitectureSection
from app.services.report.sections.evidence_section import EvidenceSection
from app.services.report.sections.hero_section import HeroSection
from app.services.report.sections.impact_section import ImpactSection
from app.services.report.sections.planning_section import PlanningSection
from app.services.report.sections.recommendation_section import RecommendationSection
from app.services.report.sections.summary_section import SummarySection
from app.services.report.sections.test_section import TestSection


class SectionFactory:
    """Creates section instances by type identifier."""

    def __init__(self) -> None:
        self._sections: Dict[str, Type[BaseSection]] = {
            "hero": HeroSection,
            "summary": SummarySection,
            "impact": ImpactSection,
            "evidence": EvidenceSection,
            "recommendations": RecommendationSection,
            "tests": TestSection,
            "actions": ActionSection,
            "architecture": ArchitectureSection,
            "planning": PlanningSection,
        }

    def create(self, section_type: str) -> BaseSection:
        section_cls = self._sections.get(section_type)
        if section_cls is None:
            raise ValueError(f"Unsupported section type: {section_type}")
        return section_cls()
