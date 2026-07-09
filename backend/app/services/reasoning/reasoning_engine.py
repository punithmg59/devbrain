"""
Reasoning Engine Orchestrator (Layer 3)

The brain of DevBrain. Connects structured evidence to engineering decisions.
All reasoning is grounded in repository evidence - never from LLM knowledge alone.
"""

import logging
from typing import Dict, Any, List

from app.services.intent.schemas import Intent
from app.services.engineering_evidence.models import EngineeringEvidence
from app.services.reasoning.schemas.engineering_decision import EngineeringDecision, DecisionType, RiskLevel
from app.services.reasoning.risk_engine import RiskEngine
from app.services.reasoning.decision_engine import DecisionEngine
from app.services.reasoning.recommendation_engine import RecommendationEngine
from app.services.reasoning.followup_engine import FollowupEngine


logger = logging.getLogger(__name__)


class ReasoningEngine:
    """
    Top-level orchestrator for Layer 3.
    Extracts decisions, recommendations, and follow-ups from structured evidence.
    """

    def __init__(self):
        self.risk_engine = RiskEngine()
        self.decision_engine = DecisionEngine()
        self.recommendation_engine = RecommendationEngine()
        self.followup_engine = FollowupEngine()

    def reason(self, intent: Intent, evidence: EngineeringEvidence) -> EngineeringDecision:
        """
        Execute the reasoning pipeline.
        
        All reasoning is grounded in repository evidence:
        - AST nodes
        - Dependency graph
        - Call graph
        - Classes and functions
        - API routes
        - Imports
        
        Never uses LLM knowledge alone - always grounded in repository data.
        
        Args:
            intent: The classified Intent from Layer 1
            evidence: The structured evidence from Layer 2
            
            Returns:
                EngineeringDecision object
        """
        logger.info(f"Reasoning over intent={intent.intent} for target={intent.target_name}")
        
        # 1. Fallback conditions for UNKNOWN decision
        if not evidence.target_name or evidence.evidence_confidence < 0.3:
            return self._build_unknown_decision(evidence, "Evidence confidence too low or target not resolved.")
            
        # 2. Compute dependencies (Downstream / Upstream)
        downstream = []
        upstream = []
        affected_files = set()
        
        if evidence.dependency_graph:
            for edge in evidence.dependency_graph.edges:
                affected_files.add(edge.file_path)
                if evidence.target_name in edge.from_node:
                    downstream.append(edge.to_node)
                elif evidence.target_name in edge.to_node:
                    upstream.append(edge.from_node)
        
        affected_files_list = list(affected_files)[:20]
        
        # 3. Component Importance & Risk
        call_count = len(upstream)
        dep_count = len(downstream)
        
        if call_count > 50 or (evidence.api_routes and len(evidence.api_routes) > 10):
            decision_val = DecisionType.CRITICAL_IMPACT
            risk_level = RiskLevel.CRITICAL
            risk_score = 90
            importance = "Highly critical. Core dependency with massive blast radius."
        elif call_count > 20 or dep_count > 20:
            decision_val = DecisionType.HIGH_IMPACT
            risk_level = RiskLevel.HIGH
            risk_score = 75
            importance = "Major component. Affects numerous upstream/downstream services."
        elif call_count > 5 or dep_count > 5:
            decision_val = DecisionType.MEDIUM_IMPACT
            risk_level = RiskLevel.MEDIUM
            risk_score = 50
            importance = "Standard component with moderate dependencies."
        elif call_count > 0 or dep_count > 0:
            decision_val = DecisionType.LOW_IMPACT
            risk_level = RiskLevel.LOW
            risk_score = 25
            importance = "Isolated component with few dependencies."
        else:
            decision_val = DecisionType.SAFE
            risk_level = RiskLevel.LOW
            risk_score = 10
            importance = "Standalone component with no tracked dependencies."
            
        # 4. Formulate the blast radius summary
        blast_summary = f"Modifying {evidence.target_name} directly affects {len(downstream)} downstream components and {len(upstream)} upstream callers across {len(affected_files)} files."
        
        # 5. Determine affected APIs
        affected_apis = [route.path for route in (evidence.api_routes or [])][:10]
        
        # 6. Build the plan and actions
        migration_plan = []
        if upstream:
            migration_plan.append(f"Update {len(upstream)} upstream consumers to point to the new implementation.")
        if downstream:
            migration_plan.append(f"Ensure backwards compatibility for {len(downstream)} downstream dependencies.")
            
        testing_checklist = [
            f"Run integration tests for {evidence.target_name}.",
            "Verify all API endpoints still return expected schemas." if affected_apis else "Run unit tests for affected files."
        ]
        
        engineering_actions = [
            "Review dependency graph to ensure no cyclical dependencies.",
            f"Update documentation for {evidence.target_name}."
        ]

        # Use legacy engines for backwards compatibility on standard UI fields
        _, legacy_summary, legacy_reason = self.decision_engine.generate_decision(
            intent, evidence, risk_level
        )
        rec_actions, req_tests, alt_options = self.recommendation_engine.generate_recommendations(
            intent, evidence, decision_val
        )
        follow_up = self.followup_engine.generate_questions(intent, decision_val)
        affected_components = self._extract_affected_components(evidence)

        decision = EngineeringDecision(
            decision=decision_val,
            risk_level=risk_level,
            risk_score=risk_score,
            confidence=evidence.evidence_confidence,
            summary=legacy_summary,
            primary_reason=legacy_reason,
            affected_components=affected_components,
            recommended_actions=rec_actions,
            alternative_options=alt_options,
            required_tests=req_tests,
            follow_up_questions=follow_up,
            
            # New fields requested by user
            risk_explanation=f"Based on {call_count} upstream callers and {dep_count} downstream dependencies.",
            component_importance=importance,
            downstream_dependencies=downstream[:20],
            upstream_callers=upstream[:20],
            blast_radius_summary=blast_summary,
            affected_files=affected_files_list,
            affected_apis=affected_apis,
            migration_plan=migration_plan if migration_plan else ["No migration required."],
            testing_checklist=testing_checklist,
            engineering_actions=engineering_actions,
        )
        
        return decision

    def _build_unknown_decision(self, evidence: EngineeringEvidence, reason: str) -> EngineeringDecision:
        return EngineeringDecision(
            decision=DecisionType.UNKNOWN,
            risk_level=RiskLevel.HIGH,
            risk_score=100,
            confidence=0.0,
            summary="Unable to generate an engineering decision.",
            primary_reason=reason,
            affected_components=[],
            recommended_actions=[],
            alternative_options=[],
            required_tests=[],
            follow_up_questions=[],
            
            risk_explanation="Insufficient repository data to calculate risk.",
            component_importance="Unknown",
            downstream_dependencies=[],
            upstream_callers=[],
            blast_radius_summary="Unknown blast radius due to lack of evidence.",
            affected_files=[],
            affected_apis=[],
            migration_plan=[],
            testing_checklist=[],
            engineering_actions=[],
        )

    def _extract_affected_components(self, evidence: EngineeringEvidence) -> List[Dict[str, Any]]:
        """Extract a simplified list of affected components for the decision payload."""
        components = []
        
        # Add repository structure data
        if evidence.classes:
            for cls in evidence.classes[:5]:
                components.append({
                    "name": cls.name,
                    "type": "class",
                    "category": "repository_structure",
                    "file": cls.file_path,
                })
        
        if evidence.functions:
            for func in evidence.functions[:10]:
                components.append({
                    "name": func.name,
                    "type": "function",
                    "category": "repository_structure",
                    "file": func.file_path,
                })
        
        if evidence.api_routes:
            for route in evidence.api_routes[:5]:
                components.append({
                    "name": route.path,
                    "type": "api_route",
                    "category": "repository_structure",
                    "file": route.file_path,
                    "method": route.method,
                })
        
        if evidence.dependency_graph:
            for edge in evidence.dependency_graph.edges[:10]:
                components.append({
                    "name": f"{edge.from_node} -> {edge.to_node}",
                    "type": "dependency",
                    "category": "repository_structure",
                    "edge_type": edge.edge_type,
                    "file": edge.file_path,
                })
        
        return components[:30]
