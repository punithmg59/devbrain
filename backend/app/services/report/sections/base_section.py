"""
Base Section Interface (Layer 4)
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.services.intent.schemas import Intent
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.report.schemas.engineering_report import ReportSectionModel


class BaseSection(ABC):
    """
    Abstract interface for all Report Composer sections.
    """

    @property
    @abstractmethod
    def section_type(self) -> str:
        """The identifier string for this section (e.g. 'impact')."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """The sort order for rendering. Lower means higher up."""
        pass

    @abstractmethod
    def build(self, intent: Intent, decision: EngineeringDecision) -> Optional[ReportSectionModel]:
        """
        Builds the section data model.
        Returns None if the section has no data to display and should be omitted.
        """
        pass
