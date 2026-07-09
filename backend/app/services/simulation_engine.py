"""Change Simulation Engine - Simulates what happens after a software change."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.entity_resolution.models import RepositoryNode, TargetType
from app.services.engineering_evidence.models import EngineeringEvidence, Criticality

logger = logging.getLogger(__name__)


class ChangeSimulationEngine:
    """Simulates the cascade effects of a software change using graph traversal."""

    def __init__(self):
        self.max_depth = 5

    async def simulate_change(
        self,
        db: AsyncSession,
        target_node: RepositoryNode,
        change_type: str,
        max_depth: int = 5,
        evidence: EngineeringEvidence = None
    ) -> dict[str, Any]:
        """
        Simulate the effects of a change to a target component.

        Args:
            db: Database session
            target_node: Resolved repository node (canonical representation)
            change_type: Type of change (delete, rename, move, extract, add)
            max_depth: Maximum traversal depth
            evidence: EngineeringEvidence for enhanced simulation (optional)

        Returns:
            Simulation result dictionary
        """
        if not target_node or not target_node.repo_id:
            return self._empty_simulation(change_type, target_node.name if target_node else "unknown", target_node.node_type.value if target_node else "unknown")

        repo_id = str(target_node.repo_id)
        node_id = str(target_node.id)

        # Traverse downstream to find affected components
        affected_nodes = await self._traverse_downstream(
            db, repo_id, node_id, max_depth
        )

        # Calculate impact metrics
        impact_metrics = self._calculate_impact_metrics(affected_nodes)

        # Detect cascade chains
        cascade_chains = self._detect_cascade_chains(affected_nodes)

        # Generate timeline
        timeline = self._generate_timeline(change_type, target_node, affected_nodes)

        # Calculate risk level - use evidence if available for more accurate assessment
        if evidence:
            risk_level, confidence = self._calculate_risk_level_from_evidence(
                change_type, evidence, impact_metrics, cascade_chains
            )
        else:
            risk_level, confidence = self._calculate_risk_level(
                change_type, impact_metrics, cascade_chains, affected_nodes
            )

        # Generate impact summary - use evidence if available
        if evidence:
            impact_summary = self._generate_impact_summary_from_evidence(
                change_type, target_node, evidence, cascade_chains
            )
        else:
            impact_summary = self._generate_impact_summary(
                change_type, target_node, affected_nodes, cascade_chains
            )

        return {
            "change_type": change_type,
            "target_component": target_node.name,
            "target_type": target_node.node_type.value,
            "risk_level": risk_level,
            "confidence": confidence,
            "impact_metrics": impact_metrics,
            "impact_summary": impact_summary,
            "timeline": timeline,
            "cascade_chains": cascade_chains,
            "affected_components": [
                {
                    "id": str(n["id"]),
                    "name": n["name"],
                    "type": n["node_type"],
                    "file": n.get("file_path", ""),
                    "depth": n.get("depth", 0),
                    "critical": n.get("depth", 0) == 1
                }
                for n in affected_nodes
            ],
            "evidence_enhanced": evidence is not None
        }

    def _calculate_risk_level_from_evidence(
        self,
        change_type: str,
        evidence: EngineeringEvidence,
        impact_metrics: dict[str, int],
        cascade_chains: list[dict[str, Any]]
    ) -> tuple[str, float]:
        """Calculate risk level using EngineeringEvidence for more accurate assessment."""
        # Base risk from evidence criticality
        if evidence.overall_criticality == Criticality.CRITICAL:
            base_risk = 0.85
        elif evidence.overall_criticality == Criticality.HIGH:
            base_risk = 0.65
        elif evidence.overall_criticality == Criticality.MEDIUM:
            base_risk = 0.45
        else:
            base_risk = 0.25

        # Adjust for change type
        change_type_multipliers = {
            "delete": 1.2,
            "rename": 1.0,
            "move": 0.9,
            "extract": 0.7,
            "add": 0.3
        }
        base_risk *= change_type_multipliers.get(change_type, 1.0)

        # Adjust for impact score
        base_risk = base_risk * (0.7 + evidence.overall_impact_score * 0.3)

        # Adjust for cascade severity
        critical_chains = sum(1 for c in cascade_chains if c["severity"] == "critical")
        if critical_chains > 0:
            base_risk += 0.15

        # Cap at 1.0
        base_risk = min(base_risk, 1.0)

        # Determine risk level
        if base_risk >= 0.8:
            risk_level = "critical"
        elif base_risk >= 0.6:
            risk_level = "high"
        elif base_risk >= 0.4:
            risk_level = "moderate"
        else:
            risk_level = "safe"

        # Confidence based on evidence confidence
        confidence = evidence.evidence_confidence
        if change_type == "delete":
            confidence = min(confidence + 0.1, 1.0)

        return risk_level, confidence

    def _generate_impact_summary_from_evidence(
        self,
        change_type: str,
        target_node: RepositoryNode,
        evidence: EngineeringEvidence,
        cascade_chains: list[dict[str, Any]]
    ) -> dict[str, list[str] | str]:
        """Generate impact summary using EngineeringEvidence."""
        critical_failures = []
        potential_runtime_errors = []
        likely_build_errors = []
        likely_test_failures = []
        configuration_impact = []

        # Use evidence groups for detailed analysis
        if evidence.runtime:
            if evidence.runtime.criticality == Criticality.CRITICAL:
                critical_failures.append(
                    f"Runtime dependencies: {evidence.runtime.critical_count} critical references will cause immediate failures"
                )
            elif evidence.runtime.criticality == Criticality.HIGH:
                potential_runtime_errors.append(
                    f"Runtime dependencies: {evidence.runtime.high_count} high-risk references may cause errors"
                )
            critical_failures.extend(evidence.runtime.risk_drivers)

        if evidence.database:
            if evidence.database.criticality == Criticality.CRITICAL:
                critical_failures.append(
                    f"Database dependencies: {evidence.database.critical_count} critical references risk data corruption"
                )
            critical_failures.extend(evidence.database.risk_drivers)

        if evidence.public_api:
            if evidence.public_api.criticality == Criticality.CRITICAL:
                critical_failures.append(
                    f"Public API dependencies: {evidence.public_api.critical_count} critical references will affect external consumers"
                )

        if evidence.configuration:
            configuration_impact.extend(evidence.configuration.risk_drivers)
            if evidence.configuration.reference_count > 0:
                configuration_impact.append(
                    f"Configuration files require updates for {evidence.configuration.reference_count} references"
                )

        if evidence.testing:
            if change_type == "delete":
                likely_test_failures.append(
                    f"Test dependencies: {evidence.testing.reference_count} test references may fail"
                )

        # Build errors from internal dependencies
        if evidence.internal_service:
            if evidence.internal_service.criticality == Criticality.CRITICAL:
                likely_build_errors.append(
                    f"Internal service dependencies: {evidence.internal_service.critical_count} critical imports will cause build failures"
                )

        # Add critical findings from evidence
        critical_failures.extend(evidence.critical_findings)

        # Deployment risk from evidence
        if evidence.deployment_risk:
            deployment_risk = evidence.deployment_risk.description
        else:
            critical_count = len(critical_failures)
            if critical_count > 5:
                deployment_risk = "High - Multiple critical dependencies affected"
            elif critical_count > 0:
                deployment_risk = "Medium - Some critical dependencies affected"
            else:
                deployment_risk = "Low - No critical dependencies affected"

        return {
            "critical_failures": critical_failures[:10],
            "potential_runtime_errors": potential_runtime_errors[:10],
            "likely_build_errors": likely_build_errors[:5],
            "likely_test_failures": likely_test_failures[:5],
            "configuration_impact": configuration_impact[:5],
            "deployment_risk": deployment_risk,
            "recommended_validations": evidence.recommended_validation_steps[:5]
        }

    async def _traverse_downstream(
        self,
        db: AsyncSession,
        repo_id: str,
        node_id: str,
        max_depth: int
    ) -> list[dict[str, Any]]:
        """Traverse downstream to find all affected components."""
        sql = text("""
            WITH RECURSIVE downstream AS (
                SELECT n.id, n.name, n.node_type,
                       COALESCE(rf.file_path, '') as file_path,
                       n.start_line, n.end_line, 0 as depth,
                       ARRAY[n.id::text] as visited
                FROM nodes n
                LEFT JOIN repo_files rf ON n.file_id = rf.id
                WHERE n.id = :node_id AND n.repo_id = :repo_id
                UNION ALL
                SELECT n2.id, n2.name, n2.node_type,
                       COALESCE(rf2.file_path, '') as file_path,
                       n2.start_line, n2.end_line, ds.depth + 1,
                       ds.visited || n2.id::text
                FROM downstream ds
                JOIN edges e ON e.from_node_id = ds.id
                JOIN nodes n2 ON n2.id = e.to_node_id
                LEFT JOIN repo_files rf2 ON n2.file_id = rf2.id
                WHERE ds.depth < :max_depth
                  AND NOT n2.id::text = ANY(ds.visited)
                  AND n2.repo_id = :repo_id
            )
            SELECT DISTINCT ON (id) id, name, node_type, file_path,
                   start_line, end_line, depth
            FROM downstream WHERE depth > 0 ORDER BY id, depth
        """)

        result = await db.execute(sql, {"node_id": node_id, "repo_id": repo_id, "max_depth": max_depth})
        return [dict(row._mapping) for row in result.mappings()]

    def _calculate_impact_metrics(self, affected_nodes: list[dict[str, Any]]) -> dict[str, int]:
        """Calculate impact metrics from affected nodes."""
        metrics = {
            "affected_apis": 0,
            "affected_services": 0,
            "affected_classes": 0,
            "affected_files": 0,
            "affected_database_tables": 0,
            "affected_workflows": 0,
            "critical_dependency_chains": 0,
            "estimated_blast_radius": len(affected_nodes)
        }

        files = set()

        for node in affected_nodes:
            node_type = node.get("node_type", "").lower()

            if "api" in node_type or "route" in node_type:
                metrics["affected_apis"] += 1
            elif "service" in node_type:
                metrics["affected_services"] += 1
            elif "class" in node_type:
                metrics["affected_classes"] += 1
            elif "table" in node_type or "database" in node_type:
                metrics["affected_database_tables"] += 1
            elif "workflow" in node_type:
                metrics["affected_workflows"] += 1

            if node.get("file_path"):
                files.add(node["file_path"])

            # Critical chains are depth 1 dependencies
            if node.get("depth", 0) == 1:
                metrics["critical_dependency_chains"] += 1

        metrics["affected_files"] = len(files)
        return metrics

    def _detect_cascade_chains(self, affected_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect critical cascade chains in the dependency graph."""
        chains = []

        # Group by depth to find chains
        by_depth: dict[int, list[dict[str, Any]]] = {}
        for node in affected_nodes:
            depth = node.get("depth", 0)
            if depth not in by_depth:
                by_depth[depth] = []
            by_depth[depth].append(node)

        # Create chains for critical paths (depth 1 -> depth 2 -> depth 3)
        if 1 in by_depth and 2 in by_depth:
            for critical_node in by_depth[1]:
                chain = {
                    "id": f"chain-{critical_node['id']}",
                    "start_component": critical_node["name"],
                    "end_component": "",
                    "steps": [
                        {
                            "id": str(critical_node["id"]),
                            "description": f"{critical_node['name']} becomes unavailable",
                            "component": critical_node["name"],
                            "componentType": critical_node["node_type"],
                            "impact": "critical" if critical_node["node_type"] in ["api_route", "service"] else "error",
                            "depth": 1
                        }
                    ],
                    "severity": "critical" if critical_node["node_type"] in ["api_route", "service"] else "high"
                }

                # Add depth 2 nodes
                if 2 in by_depth:
                    for depth2_node in by_depth[2][:3]:  # Limit to 3 for performance
                        chain["steps"].append({
                            "id": str(depth2_node["id"]),
                            "description": f"{depth2_node['name']} affected by {critical_node['name']}",
                            "component": depth2_node["name"],
                            "componentType": depth2_node["node_type"],
                            "impact": "error",
                            "depth": 2
                        })
                        chain["end_component"] = depth2_node["name"]

                chains.append(chain)

        return chains

    def _generate_timeline(
        self,
        change_type: str,
        target_node: RepositoryNode,
        affected_nodes: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate a timeline of cascade effects."""
        timeline = []

        # Initial change
        timeline.append({
            "id": "step-0",
            "description": f"{change_type.capitalize()} {target_node.name}",
            "component": target_node.name,
            "componentType": target_node.node_type.value,
            "impact": "info",
            "depth": 0
        })

        # Group by depth and add to timeline
        by_depth: dict[int, list[dict[str, Any]]] = {}
        for node in affected_nodes:
            depth = node.get("depth", 0)
            if depth not in by_depth:
                by_depth[depth] = []
            by_depth[depth].append(node)

        # Add steps for each depth level
        for depth in sorted(by_depth.keys()):
            nodes_at_depth = by_depth[depth]
            # Limit to 5 nodes per depth for performance
            for node in nodes_at_depth[:5]:
                impact = "critical" if depth == 1 and node["node_type"] in ["api_route", "service"] else "error"
                timeline.append({
                    "id": f"step-{depth}-{node['id']}",
                    "description": f"{node['name']} fails",
                    "component": node["name"],
                    "componentType": node["node_type"],
                    "impact": impact,
                    "depth": depth
                })

        return timeline

    def _calculate_risk_level(
        self,
        change_type: str,
        impact_metrics: dict[str, int],
        cascade_chains: list[dict[str, Any]],
        affected_nodes: list[dict[str, Any]]
    ) -> tuple[str, float]:
        """Calculate risk level and confidence score."""
        # Base risk by change type
        risk_scores = {
            "delete": 0.8,
            "rename": 0.5,
            "move": 0.4,
            "extract": 0.3,
            "add": 0.1
        }
        base_risk = risk_scores.get(change_type, 0.5)

        # Adjust for impact metrics
        if impact_metrics["affected_apis"] > 0:
            base_risk += 0.3
        if impact_metrics["critical_dependency_chains"] > 5:
            base_risk += 0.2
        if impact_metrics["affected_services"] > 0:
            base_risk += 0.2

        # Adjust for cascade severity
        critical_chains = sum(1 for c in cascade_chains if c["severity"] == "critical")
        if critical_chains > 0:
            base_risk += 0.3

        # Cap at 1.0
        base_risk = min(base_risk, 1.0)

        # Determine risk level
        if base_risk >= 0.8:
            risk_level = "critical"
        elif base_risk >= 0.6:
            risk_level = "high"
        elif base_risk >= 0.4:
            risk_level = "moderate"
        else:
            risk_level = "safe"

        # Confidence based on data quality
        confidence = 0.9 if len(affected_nodes) > 0 else 0.5
        if change_type == "delete" and len(affected_nodes) > 0:
            confidence = 0.95

        return risk_level, confidence

    def _generate_impact_summary(
        self,
        change_type: str,
        target_node: RepositoryNode,
        affected_nodes: list[dict[str, Any]],
        cascade_chains: list[dict[str, Any]]
    ) -> dict[str, list[str] | str]:
        """Generate impact summary."""
        critical_failures = []
        potential_runtime_errors = []
        likely_build_errors = []
        likely_test_failures = []
        configuration_impact = []

        # Critical failures
        for node in affected_nodes:
            if node.get("depth", 0) == 1 and node["node_type"] in ["api_route", "service"]:
                critical_failures.append(f"{node['name']} ({node['node_type']}) becomes unavailable")

        # Runtime errors
        for node in affected_nodes:
            if node["node_type"] in ["function", "method"]:
                potential_runtime_errors.append(f"{node['name']} may throw runtime errors")

        # Build errors
        if change_type == "delete":
            likely_build_errors.append(f"Import errors in files referencing {target_node.name}")
            likely_build_errors.append(f"Type errors for {target_node.name} references")

        # Test failures
        if len(affected_nodes) > 0:
            likely_test_failures.append(f"Tests for {len(affected_nodes)} affected components may fail")

        # Configuration impact
        if target_node.node_type in [TargetType.SERVICE, TargetType.API, TargetType.API_ROUTE]:
            configuration_impact.append(f"Configuration for {target_node.name} may need updates")

        # Deployment risk
        critical_count = len(critical_failures)
        if critical_count > 5:
            deployment_risk = "High - Multiple critical services affected"
        elif critical_count > 0:
            deployment_risk = "Medium - Some critical services affected"
        else:
            deployment_risk = "Low - No critical services affected"

        return {
            "critical_failures": critical_failures[:10],  # Limit to 10
            "potential_runtime_errors": potential_runtime_errors[:10],
            "likely_build_errors": likely_build_errors[:5],
            "likely_test_failures": likely_test_failures[:5],
            "configuration_impact": configuration_impact[:5],
            "deployment_risk": deployment_risk
        }

    def _empty_simulation(
        self,
        change_type: str,
        target_name: str,
        target_type: str
    ) -> dict[str, Any]:
        """Return empty simulation when target not found."""
        return {
            "change_type": change_type,
            "target_component": target_name,
            "target_type": target_type or "unknown",
            "risk_level": "safe",
            "confidence": 0.5,
            "impact_metrics": {
                "affected_apis": 0,
                "affected_services": 0,
                "affected_classes": 0,
                "affected_files": 0,
                "affected_database_tables": 0,
                "affected_workflows": 0,
                "critical_dependency_chains": 0,
                "estimated_blast_radius": 0
            },
            "impact_summary": {
                "critical_failures": [],
                "potential_runtime_errors": [],
                "likely_build_errors": [],
                "likely_test_failures": [],
                "configuration_impact": [],
                "deployment_risk": "Low - Target not found in repository"
            },
            "timeline": [],
            "cascade_chains": [],
            "affected_components": []
        }
