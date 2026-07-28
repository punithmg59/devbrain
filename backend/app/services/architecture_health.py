import logging
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Edge, Node
from app.schemas.architecture import ArchitectureHealthReport, Hotspot

logger = logging.getLogger(__name__)

class ArchitectureHealthService:
    @staticmethod
    async def evaluate_health(repo_id: UUID, db: AsyncSession) -> ArchitectureHealthReport:
        # Fetch all nodes and edges for the repository
        nodes_result = await db.execute(select(Node).where(Node.repo_id == repo_id))
        nodes = nodes_result.scalars().all()
        
        edges_result = await db.execute(select(Edge).where(Edge.repo_id == repo_id))
        edges = edges_result.scalars().all()

        if not nodes:
            return ArchitectureHealthReport(
                overall_score=100,
                architecture_health="Excellent",
                complexity_score=100,
                coupling_score=100,
                maintainability_score=100,
                risk_score=100,
                hotspots=[],
                recommendations=["No nodes found in repository."]
            )

        # Build graph representations
        node_map = {str(n.id): n for n in nodes}
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)
        
        for e in edges:
            from_id = str(e.from_node_id)
            to_id = str(e.to_node_id)
            out_degree[from_id] += 1
            in_degree[to_id] += 1
            
        total_nodes = len(nodes)
        total_edges = len(edges)
        
        # --- 1. Complexity Score ---
        # Based on edges, callees, callers, API counts.
        avg_degree = total_edges / total_nodes
        api_count = sum(1 for n in nodes if n.node_type == "api_route")
        
        # Heuristic: 1 edge per node is 100%. If avg_degree hits 10, it drops to 0.
        complexity_raw = (avg_degree * 10) + (api_count / total_nodes * 20 if total_nodes > 0 else 0)
        complexity_score = max(0, min(100, int(100 - complexity_raw)))
        
        # --- 2. Coupling Score ---
        # Based on many dependencies and imports.
        # n.imports is an ARRAY column, not a relationship, so no lazy-loading risk
        avg_imports = sum(len(n.imports) if n.imports else 0 for n in nodes) / total_nodes
        coupling_raw = (avg_imports * 5) + (avg_degree * 5)
        coupling_score = max(0, min(100, int(100 - coupling_raw)))
        
        # --- 3. Maintainability Score ---
        # Based on fan-in, fan-out, density
        graph_density = total_edges / (total_nodes * (total_nodes - 1)) if total_nodes > 1 else 0
        high_fan_out_count = sum(1 for d in out_degree.values() if d > 10)
        maintainability_raw = (graph_density * 1000) + (high_fan_out_count / total_nodes * 500)
        maintainability_score = max(0, min(100, int(100 - maintainability_raw)))
        
        # --- 4. Risk Score ---
        # Based on centrality and dependency concentration.
        centrality_sum = 0
        critical_node_count = 0
        for n_id in node_map:
            # Approximation of centrality: in * out
            centr = in_degree[n_id] * out_degree[n_id]
            centrality_sum += centr
            if centr > 50:
                critical_node_count += 1
                
        avg_centrality = centrality_sum / total_nodes
        risk_raw = (avg_centrality * 2) + (critical_node_count / total_nodes * 200)
        risk_score = max(0, min(100, int(100 - risk_raw)))

        # --- Overall Score ---
        overall_score = int((complexity_score + coupling_score + maintainability_score + risk_score) / 4)
        
        if overall_score >= 90:
            health = "Excellent"
        elif overall_score >= 75:
            health = "Healthy"
        elif overall_score >= 60:
            health = "Moderate Risk"
        elif overall_score >= 40:
            health = "High Risk"
        else:
            health = "Critical"
            
        # --- Hotspot Detection ---
        hotspots = []
        for n_id, n in node_map.items():
            in_d = in_degree[n_id]
            out_d = out_degree[n_id]
            centr = in_d * out_d
            
            if out_d > 15:
                hotspots.append(Hotspot(node_id=n_id, node_name=n.name, risk_level="High Risk", reason=f"Excessive fan-out ({out_d} dependencies)"))
            elif in_d > 25:
                hotspots.append(Hotspot(node_id=n_id, node_name=n.name, risk_level="Moderate Risk", reason=f"High fan-in ({in_d} callers)"))
            elif centr > 100:
                hotspots.append(Hotspot(node_id=n_id, node_name=n.name, risk_level="Critical", reason=f"High centrality bottleneck"))
                
        # Limit to top 15 hotspots
        risk_weights = {"Critical": 4, "High Risk": 3, "Moderate Risk": 2}
        hotspots = sorted(hotspots, key=lambda x: risk_weights.get(x.risk_level, 1), reverse=True)[:15]
        
        # --- Recommendations Generation ---
        recommendations = []
        if coupling_score < 60:
            recommendations.append("High overall coupling detected. Consider reducing cross-module imports and introducing abstractions.")
        if maintainability_score < 60:
            recommendations.append("Several components have excessive dependencies. Refactor large functions/classes.")
        if risk_score < 60:
            recommendations.append("Graph reveals tight bottlenecks. De-couple highly centralized hubs.")
            
        # Include specific hotspot advice
        for h in hotspots[:5]:
            if "fan-out" in h.reason:
                recommendations.append(f"Function or class '{h.node_name}' has excessive fan-out. Consider breaking it down.")
            elif "bottleneck" in h.reason:
                recommendations.append(f"Component '{h.node_name}' is an architectural bottleneck.")
            elif "fan-in" in h.reason:
                recommendations.append(f"Component '{h.node_name}' is heavily relied upon. Ensure it is robustly tested.")
                
        # Deduplicate and limit
        unique_recs = []
        for rec in recommendations:
            if rec not in unique_recs:
                unique_recs.append(rec)
                
        return ArchitectureHealthReport(
            overall_score=overall_score,
            architecture_health=health,
            complexity_score=complexity_score,
            coupling_score=coupling_score,
            maintainability_score=maintainability_score,
            risk_score=risk_score,
            hotspots=hotspots,
            recommendations=unique_recs[:10]
        )
