from typing import Optional
from app.services.intent.schemas import Intent
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision
from app.services.engineering_evidence.models import EngineeringEvidence
from app.services.report.schemas.engineering_report import ReportSectionModel
from .base_section import BaseSection


class EvidenceSection(BaseSection):
    @property
    def section_type(self) -> str:
        return "evidence"

    @property
    def priority(self) -> int:
        return 30

    def build(
        self, 
        intent: Intent, 
        decision: EngineeringDecision,
        evidence: Optional[EngineeringEvidence] = None
    ) -> Optional[ReportSectionModel]:
        content = {
            "reasoning": decision.primary_reason,
            "affected_components": decision.affected_components,
        }
        
        # If EngineeringEvidence is available, add rich evidence data
        if evidence:
            content["overall_summary"] = evidence.overall_summary
            content["total_references"] = evidence.total_references
            content["overall_criticality"] = evidence.overall_criticality.value
            content["overall_impact_score"] = evidence.overall_impact_score
            content["overall_confidence"] = evidence.overall_confidence
            content["evidence_confidence"] = evidence.evidence_confidence
            
            # Add evidence groups
            evidence_groups = {}
            if evidence.runtime:
                evidence_groups["runtime"] = {
                    "count": evidence.runtime.reference_count,
                    "criticality": evidence.runtime.criticality.value,
                    "impact_score": evidence.runtime.impact_score,
                    "summary": evidence.runtime.engineering_summary,
                    "affected_systems": evidence.runtime.affected_systems,
                    "risk_drivers": evidence.runtime.risk_drivers,
                }
            if evidence.configuration:
                evidence_groups["configuration"] = {
                    "count": evidence.configuration.reference_count,
                    "criticality": evidence.configuration.criticality.value,
                    "impact_score": evidence.configuration.impact_score,
                    "summary": evidence.configuration.engineering_summary,
                    "affected_systems": evidence.configuration.affected_systems,
                    "risk_drivers": evidence.configuration.risk_drivers,
                }
            if evidence.infrastructure:
                evidence_groups["infrastructure"] = {
                    "count": evidence.infrastructure.reference_count,
                    "criticality": evidence.infrastructure.criticality.value,
                    "impact_score": evidence.infrastructure.impact_score,
                    "summary": evidence.infrastructure.engineering_summary,
                    "affected_systems": evidence.infrastructure.affected_systems,
                    "risk_drivers": evidence.infrastructure.risk_drivers,
                }
            if evidence.database:
                evidence_groups["database"] = {
                    "count": evidence.database.reference_count,
                    "criticality": evidence.database.criticality.value,
                    "impact_score": evidence.database.impact_score,
                    "summary": evidence.database.engineering_summary,
                    "affected_systems": evidence.database.affected_systems,
                    "risk_drivers": evidence.database.risk_drivers,
                }
            if evidence.testing:
                evidence_groups["testing"] = {
                    "count": evidence.testing.reference_count,
                    "criticality": evidence.testing.criticality.value,
                    "impact_score": evidence.testing.impact_score,
                    "summary": evidence.testing.engineering_summary,
                    "affected_systems": evidence.testing.affected_systems,
                    "risk_drivers": evidence.testing.risk_drivers,
                }
            if evidence.public_api:
                evidence_groups["public_api"] = {
                    "count": evidence.public_api.reference_count,
                    "criticality": evidence.public_api.criticality.value,
                    "impact_score": evidence.public_api.impact_score,
                    "summary": evidence.public_api.engineering_summary,
                    "affected_systems": evidence.public_api.affected_systems,
                    "risk_drivers": evidence.public_api.risk_drivers,
                }
            if evidence.internal_service:
                evidence_groups["internal_service"] = {
                    "count": evidence.internal_service.reference_count,
                    "criticality": evidence.internal_service.criticality.value,
                    "impact_score": evidence.internal_service.impact_score,
                    "summary": evidence.internal_service.engineering_summary,
                    "affected_systems": evidence.internal_service.affected_systems,
                    "risk_drivers": evidence.internal_service.risk_drivers,
                }
            
            content["evidence_groups"] = evidence_groups
            
            # Add risk assessments
            risk_assessments = {}
            if evidence.deployment_risk:
                risk_assessments["deployment"] = {
                    "level": evidence.deployment_risk.risk_level.value,
                    "score": evidence.deployment_risk.risk_score,
                    "description": evidence.deployment_risk.description,
                    "affected_systems": evidence.deployment_risk.affected_systems,
                }
            if evidence.runtime_risk:
                risk_assessments["runtime"] = {
                    "level": evidence.runtime_risk.risk_level.value,
                    "score": evidence.runtime_risk.risk_score,
                    "description": evidence.runtime_risk.description,
                    "affected_systems": evidence.runtime_risk.affected_systems,
                }
            if evidence.testing_risk:
                risk_assessments["testing"] = {
                    "level": evidence.testing_risk.risk_level.value,
                    "score": evidence.testing_risk.risk_score,
                    "description": evidence.testing_risk.description,
                    "affected_systems": evidence.testing_risk.affected_systems,
                }
            if evidence.configuration_risk:
                risk_assessments["configuration"] = {
                    "level": evidence.configuration_risk.risk_level.value,
                    "score": evidence.configuration_risk.risk_score,
                    "description": evidence.configuration_risk.description,
                    "affected_systems": evidence.configuration_risk.affected_systems,
                }
            if evidence.database_risk:
                risk_assessments["database"] = {
                    "level": evidence.database_risk.risk_level.value,
                    "score": evidence.database_risk.risk_score,
                    "description": evidence.database_risk.description,
                    "affected_systems": evidence.database_risk.affected_systems,
                }
            
            content["risk_assessments"] = risk_assessments
            
            # Add critical findings
            content["critical_findings"] = evidence.critical_findings
            
            # Add affected systems
            content["affected_systems"] = evidence.affected_systems
            
            # Add recommended validation steps
            content["recommended_validation_steps"] = evidence.recommended_validation_steps
        
        return ReportSectionModel(
            type=self.section_type,
            title="Engineering Evidence",
            priority=self.priority,
            content=content
        )
