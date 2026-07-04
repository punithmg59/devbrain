from typing import List, Dict, Set, Tuple, Optional
from uuid import UUID
from collections import deque, defaultdict
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Node, Edge, Workflow, WorkflowNode
from app.models.intent import Intent
from app.schemas.impact_analysis import (
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
    AffectedEntity,
    BlastRadiusResult,
    ComplexityScore,
    DifficultyScore,
    ChangeStep,
    RiskScore,
)
from app.schemas.evidence import NodeEvidence, WorkflowEvidence


class GraphTraversal:
    """Graph traversal algorithms for impact analysis."""
    
    @staticmethod
    def bfs_blast_radius(
        start_node_id: UUID,
        edges: List[Edge],
        max_depth: int = 5,
        direction: str = "both"
    ) -> Tuple[Set[UUID], Dict[UUID, int]]:
        """
        Perform BFS to calculate blast radius.
        
        Returns:
            Tuple of (affected_node_ids, distance_map)
        """
        affected = set()
        distance_map = {}
        queue = deque([(start_node_id, 0)])
        
        # Build adjacency list
        adj = defaultdict(list)
        for edge in edges:
            if direction in ["outgoing", "both"]:
                adj[str(edge.from_node_id)].append(str(edge.to_node_id))
            if direction in ["incoming", "both"]:
                adj[str(edge.to_node_id)].append(str(edge.from_node_id))
        
        while queue:
            node_id, depth = queue.popleft()
            
            if depth > max_depth:
                continue
            
            if node_id in affected:
                continue
            
            affected.add(node_id)
            distance_map[node_id] = depth
            
            for neighbor in adj.get(node_id, []):
                if neighbor not in affected:
                    queue.append((neighbor, depth + 1))
        
        return affected, distance_map
    
    @staticmethod
    def topological_sort(nodes: Set[UUID], edges: List[Edge]) -> List[UUID]:
        """
        Perform topological sort for dependency ordering.
        
        Returns:
            List of node IDs in dependency order
        """
        # Build adjacency list and in-degree count
        adj = defaultdict(list)
        in_degree = defaultdict(int)
        
        node_set = {str(n) for n in nodes}
        
        for edge in edges:
            from_id = str(edge.from_node_id)
            to_id = str(edge.to_node_id)
            
            if from_id in node_set and to_id in node_set:
                adj[from_id].append(to_id)
                in_degree[to_id] += 1
        
        # Initialize queue with nodes having no dependencies
        queue = deque([node for node in node_set if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(UUID(node))
            
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    @staticmethod
    def find_cyclic_dependencies(nodes: Set[UUID], edges: List[Edge]) -> List[List[UUID]]:
        """
        Find cyclic dependencies using DFS.
        
        Returns:
            List of cycles (each cycle is a list of node IDs)
        """
        node_set = {str(n) for n in nodes}
        adj = defaultdict(list)
        
        for edge in edges:
            from_id = str(edge.from_node_id)
            to_id = str(edge.to_node_id)
            
            if from_id in node_set and to_id in node_set:
                adj[from_id].append(to_id)
        
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in adj[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycles.append([UUID(n) for n in path[cycle_start:]])
                    return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for node in node_set:
            if node not in visited:
                dfs(node)
        
        return cycles


class RiskScoring:
    """Deterministic risk scoring algorithms."""
    
    @staticmethod
    def calculate_risk_score(
        blast_radius: BlastRadiusResult,
        affected_services: List[AffectedEntity],
        affected_databases: List[AffectedEntity],
        affected_workflows: List[WorkflowEvidence],
        complexity: ComplexityScore
    ) -> RiskScore:
        """
        Calculate overall risk score using deterministic algorithm.
        
        Risk factors:
        - Blast radius (number of affected entities)
        - Dependency risk (number of critical dependencies)
        - Complexity risk (code complexity)
        - Workflow risk (number of affected workflows)
        - API risk (number of breaking APIs)
        - Database risk (number of affected databases)
        """
        # Normalize each factor to 0-100 scale
        
        # Blast radius risk
        total_entities = blast_radius.total_affected_entities
        blast_risk = min((total_entities / 100) * 100, 100.0)
        
        # Dependency risk
        critical_deps = sum(1 for e in affected_services if e.impact_level in ["critical", "high"])
        dep_risk = min((critical_deps / 10) * 100, 100.0)
        
        # Complexity risk
        complexity_risk = complexity.overall_score
        
        # Workflow risk
        critical_workflows = sum(1 for w in affected_workflows if w.criticality == "high")
        workflow_risk = min((critical_workflows / 5) * 100, 100.0)
        
        # API risk (breaking APIs)
        api_risk = min((len(affected_services) / 20) * 100, 100.0)
        
        # Database risk
        db_risk = min((len(affected_databases) / 10) * 100, 100.0)
        
        # Weighted overall risk
        weights = {
            "blast_radius": 0.25,
            "dependency": 0.20,
            "complexity": 0.20,
            "workflow": 0.15,
            "api": 0.10,
            "database": 0.10,
        }
        
        overall_risk = (
            blast_risk * weights["blast_radius"] +
            dep_risk * weights["dependency"] +
            complexity_risk * weights["complexity"] +
            workflow_risk * weights["workflow"] +
            api_risk * weights["api"] +
            db_risk * weights["database"]
        )
        
        # Determine risk category
        if overall_risk >= 80:
            category = "critical"
        elif overall_risk >= 60:
            category = "high"
        elif overall_risk >= 40:
            category = "medium"
        elif overall_risk >= 20:
            category = "low"
        else:
            category = "safe"
        
        # Build risk factors dict
        risk_factors = {
            "blast_radius_entities": total_entities,
            "critical_dependencies": critical_deps,
            "complexity_score": complexity.overall_score,
            "critical_workflows": critical_workflows,
            "affected_apis": len(affected_services),
            "affected_databases": len(affected_databases),
        }
        
        return RiskScore(
            overall_risk_score=round(overall_risk, 2),
            risk_category=category,
            confidence=0.85,  # Deterministic algorithm has high confidence
            blast_radius_risk=round(blast_risk, 2),
            dependency_risk=round(dep_risk, 2),
            complexity_risk=round(complexity_risk, 2),
            workflow_risk=round(workflow_risk, 2),
            api_risk=round(api_risk, 2),
            database_risk=round(db_risk, 2),
            risk_factors=risk_factors,
        )


class ComplexityScoring:
    """Deterministic complexity scoring algorithms."""
    
    @staticmethod
    def calculate_complexity(
        target_node: Optional[Node],
        affected_nodes: List[Node],
        edges: List[Edge]
    ) -> ComplexityScore:
        """
        Calculate engineering complexity score.
        
        Factors:
        - Cyclomatic complexity (from node data)
        - Dependency complexity (number of dependencies)
        - Coupling complexity (interconnectedness)
        - Data complexity (data structures)
        - Control flow complexity (branching)
        """
        if not target_node:
            # Default complexity when no target node
            return ComplexityScore(
                overall_score=50.0,
                cyclomatic_complexity=50.0,
                dependency_complexity=50.0,
                coupling_complexity=50.0,
                data_complexity=50.0,
                control_flow_complexity=50.0,
            )
        
        # Cyclomatic complexity (from node's complexity_score)
        cyclomatic = min(target_node.complexity_score * 10, 100.0)
        
        # Dependency complexity (number of edges)
        dep_complexity = min(len(edges) * 2, 100.0)
        
        # Coupling complexity (average degree)
        if affected_nodes:
            avg_degree = len(edges) / max(len(affected_nodes), 1)
            coupling = min(avg_degree * 10, 100.0)
        else:
            coupling = 50.0
        
        # Data complexity (based on node type and imports)
        data_complexity = 50.0
        if target_node.imports:
            data_complexity = min(len(target_node.imports) * 5, 100.0)
        
        # Control flow complexity (based on calls)
        control_flow = 50.0
        if target_node.calls:
            control_flow = min(len(target_node.calls) * 3, 100.0)
        
        # Overall complexity (weighted average)
        overall = (
            cyclomatic * 0.3 +
            dep_complexity * 0.25 +
            coupling * 0.2 +
            data_complexity * 0.15 +
            control_flow * 0.1
        )
        
        return ComplexityScore(
            overall_score=round(overall, 2),
            cyclomatic_complexity=round(cyclomatic, 2),
            dependency_complexity=round(dep_complexity, 2),
            coupling_complexity=round(coupling, 2),
            data_complexity=round(data_complexity, 2),
            control_flow_complexity=round(control_flow, 2),
        )


class DifficultyScoring:
    """Deterministic difficulty scoring algorithms."""
    
    @staticmethod
    def calculate_difficulty(
        complexity: ComplexityScore,
        blast_radius: BlastRadiusResult,
        affected_databases: List[AffectedEntity]
    ) -> Tuple[DifficultyScore, DifficultyScore]:
        """
        Calculate implementation and migration difficulty.
        
        Returns:
            Tuple of (implementation_difficulty, migration_difficulty)
        """
        # Implementation difficulty
        technical = min(complexity.overall_score * 0.8 + blast_radius.total_affected_entities * 0.5, 100.0)
        testing = min(blast_radius.total_affected_entities * 2, 100.0)
        deployment = min(len(affected_databases) * 15 + 20, 100.0)
        rollback = deployment * 1.2  # Rollback is harder than deployment
        
        impl_overall = (technical * 0.4 + testing * 0.3 + deployment * 0.2 + rollback * 0.1)
        
        # Migration difficulty
        migration = min(len(affected_databases) * 20 + complexity.data_complexity * 0.5, 100.0)
        
        impl_difficulty = DifficultyScore(
            overall_score=round(min(impl_overall, 100.0), 2),
            technical_difficulty=round(min(technical, 100.0), 2),
            testing_difficulty=round(min(testing, 100.0), 2),
            deployment_difficulty=round(min(deployment, 100.0), 2),
            migration_difficulty=round(min(migration, 100.0), 2),
            rollback_difficulty=round(min(rollback, 100.0), 2),
        )
        
        mig_difficulty = DifficultyScore(
            overall_score=round(min(migration, 100.0), 2),
            technical_difficulty=round(min(migration * 0.8, 100.0), 2),
            testing_difficulty=round(min(migration * 0.6, 100.0), 2),
            deployment_difficulty=round(min(migration * 0.9, 100.0), 2),
            migration_difficulty=round(min(migration, 100.0), 2),
            rollback_difficulty=round(min(migration * 1.1, 100.0), 2),
        )
        
        return impl_difficulty, mig_difficulty


class ChangeOrdering:
    """Deterministic change ordering algorithms."""
    
    @staticmethod
    def calculate_change_order(
        affected_entities: List[AffectedEntity],
        edges: List[Edge],
        complexity: ComplexityScore
    ) -> Tuple[List[ChangeStep], float]:
        """
        Calculate recommended order of changes using topological sort.
        
        Returns:
            Tuple of (change_steps, total_effort_hours)
        """
        # Group entities by type and impact level
        entity_map = {str(e.id): e for e in affected_entities}
        node_ids = {e.id for e in affected_entities}
        
        # Get topological order
        try:
            ordered_ids = GraphTraversal.topological_sort(node_ids, edges)
        except:
            # Fallback to simple ordering if topological sort fails
            ordered_ids = list(node_ids)
        
        # Create change steps
        steps = []
        total_effort = 0.0
        
        for i, node_id in enumerate(ordered_ids):
            entity = entity_map.get(str(node_id))
            if not entity:
                continue
            
            # Estimate effort based on complexity and impact
            base_effort = 2.0  # Base 2 hours per change
            complexity_multiplier = complexity.overall_score / 50.0
            impact_multiplier = {
                "critical": 2.0,
                "high": 1.5,
                "medium": 1.0,
                "low": 0.5,
            }.get(entity.impact_level, 1.0)
            
            effort = base_effort * complexity_multiplier * impact_multiplier
            total_effort += effort
            
            # Determine risk level
            risk_level = entity.impact_level
            
            step = ChangeStep(
                step_number=i + 1,
                entity_id=entity.id,
                entity_name=entity.name,
                entity_type=entity.entity_type,
                action="modify",  # Default action
                dependencies=[],
                estimated_effort_hours=round(effort, 2),
                risk_level=risk_level,
                blocking_for=[],
            )
            
            steps.append(step)
        
        return steps, round(total_effort, 2)


class ImpactAnalysisEngine:
    """
    Main Impact Analysis Engine service.
    
    This deterministic engine uses graph algorithms, dependency analysis,
    and repository intelligence to calculate engineering impact without LLM.
    Designed for repositories with over 100,000 files.
    """
    
    def __init__(self):
        self.graph_traversal = GraphTraversal()
        self.risk_scoring = RiskScoring()
        self.complexity_scoring = ComplexityScoring()
        self.difficulty_scoring = DifficultyScoring()
        self.change_ordering = ChangeOrdering()
    
    async def analyze_impact(
        self,
        request: ImpactAnalysisRequest,
        db: AsyncSession
    ) -> ImpactAnalysisResponse:
        """
        Perform comprehensive impact analysis.
        
        Args:
            request: Impact analysis request
            db: Database session
            
        Returns:
            ImpactAnalysisResponse with structured engineering data
        """
        # Find target node
        target_node = await self._find_target_node(request, db)
        if not target_node:
            return self._empty_response(request)
        
        # Get edges for traversal
        edges = await self._get_edges(request.repo_id, db)
        
        # Calculate blast radius
        blast_radius = await self._calculate_blast_radius(
            target_node.id, edges, request.max_depth, request.include_indirect, db
        )
        
        # Get affected nodes
        affected_node_ids = set()
        for entity_list in [
            blast_radius.affected_services,
            blast_radius.affected_apis,
            blast_radius.affected_databases,
            blast_radius.affected_functions
        ]:
            affected_node_ids.update(e.id for e in entity_list)
        
        affected_nodes = await self._fetch_nodes_by_ids(list(affected_node_ids), db)
        
        # Calculate complexity
        complexity = self.complexity_scoring.calculate_complexity(
            target_node, affected_nodes, edges
        )
        
        # Get affected workflows
        affected_workflows = await self._get_affected_workflows(target_node.id, db)
        
        # Calculate risk score
        risk_score = self.risk_scoring.calculate_risk_score(
            blast_radius,
            blast_radius.affected_services,
            blast_radius.affected_databases,
            affected_workflows,
            complexity
        )
        
        # Calculate difficulty
        impl_difficulty, mig_difficulty = self.difficulty_scoring.calculate_difficulty(
            complexity, blast_radius, blast_radius.affected_databases
        )
        
        # Calculate change order
        all_affected = (
            blast_radius.affected_services +
            blast_radius.affected_apis +
            blast_radius.affected_databases +
            blast_radius.affected_functions
        )
        change_order, total_effort = self.change_ordering.calculate_change_order(
            all_affected, edges, complexity
        )
        
        # Identify breaking changes
        breaking_apis = [e for e in blast_radius.affected_apis if e.impact_level in ["critical", "high"]]
        breaking_services = [e for e in blast_radius.affected_services if e.impact_level in ["critical", "high"]]
        breaking_databases = [e for e in blast_radius.affected_databases if e.impact_level in ["critical", "high"]]
        
        return ImpactAnalysisResponse(
            intent=request.intent,
            target=request.target,
            target_node_id=target_node.id,
            risk_score=risk_score,
            blast_radius=blast_radius,
            breaking_apis=breaking_apis,
            breaking_services=breaking_services,
            breaking_databases=breaking_databases,
            affected_services=blast_radius.affected_services,
            affected_databases=blast_radius.affected_databases,
            affected_workflows=affected_workflows,
            engineering_complexity=complexity,
            migration_difficulty=mig_difficulty,
            implementation_difficulty=impl_difficulty,
            recommended_change_order=change_order,
            total_estimated_effort_hours=total_effort,
            analysis_method="graph_traversal",
            analysis_timestamp=datetime.utcnow().isoformat(),
            nodes_analyzed=len(affected_nodes) + 1,
            edges_traversed=len(edges),
        )
    
    async def _find_target_node(
        self,
        request: ImpactAnalysisRequest,
        db: AsyncSession
    ) -> Optional[Node]:
        """Find the target node."""
        if request.target_node_id:
            result = await db.execute(
                select(Node).where(Node.id == request.target_node_id)
            )
            return result.scalar_one_or_none()
        
        result = await db.execute(
            select(Node)
            .where(
                and_(
                    Node.repo_id == request.repo_id,
                    or_(
                        Node.name.ilike(f"%{request.target}%"),
                        Node.full_path.ilike(f"%{request.target}%"),
                    )
                )
            )
            .order_by(Node.complexity_score.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _get_edges(self, repo_id: UUID, db: AsyncSession) -> List[Edge]:
        """Get all edges for the repository."""
        result = await db.execute(
            select(Edge).where(Edge.repo_id == repo_id)
        )
        return list(result.scalars().all())
    
    async def _calculate_blast_radius(
        self,
        start_node_id: UUID,
        edges: List[Edge],
        max_depth: int,
        include_indirect: bool,
        db: AsyncSession
    ) -> BlastRadiusResult:
        """Calculate blast radius using graph traversal."""
        direction = "both" if include_indirect else "outgoing"
        affected_ids, distance_map = self.graph_traversal.bfs_blast_radius(
            start_node_id, edges, max_depth, direction
        )
        
        # Fetch affected nodes
        affected_nodes = await self._fetch_nodes_by_ids(list(affected_ids), db)
        
        # Categorize by type
        services = []
        apis = []
        databases = []
        functions = []
        
        for node in affected_nodes:
            distance = distance_map.get(str(node.id), 0)
            is_direct = distance == 0 or distance == 1
            
            # Determine impact level based on distance and complexity
            if distance == 0:
                impact_level = "critical"
            elif distance == 1:
                impact_level = "high"
            elif distance <= 2:
                impact_level = "medium"
            else:
                impact_level = "low"
            
            entity = AffectedEntity(
                id=node.id,
                name=node.name,
                entity_type=node.node_type,
                impact_level=impact_level,
                dependency_distance=distance,
                is_direct=is_direct,
                risk_contribution=min(1.0 - (distance / max_depth), 1.0),
            )
            
            if node.node_type == "service":
                services.append(entity)
            elif node.node_type == "api_route":
                apis.append(entity)
            elif node.node_type == "model":
                databases.append(entity)
            elif node.node_type == "function":
                functions.append(entity)
        
        direct_count = sum(1 for e in [services, apis, databases, functions] if any(x.is_direct for x in e))
        indirect_count = len(affected_nodes) - direct_count
        
        return BlastRadiusResult(
            total_affected_entities=len(affected_nodes),
            direct_dependencies=direct_count,
            indirect_dependencies=indirect_count,
            affected_services=services,
            affected_apis=apis,
            affected_databases=databases,
            affected_functions=functions,
            max_depth_reached=max(distance_map.values()) if distance_map else 0,
            traversal_complete=True,
        )
    
    async def _fetch_nodes_by_ids(self, node_ids: List[UUID], db: AsyncSession) -> List[Node]:
        """Fetch nodes by IDs."""
        if not node_ids:
            return []
        result = await db.execute(
            select(Node).where(Node.id.in_(node_ids))
        )
        return list(result.scalars().all())
    
    async def _get_affected_workflows(self, target_node_id: UUID, db: AsyncSession) -> List[WorkflowEvidence]:
        """Get workflows that include the target node."""
        result = await db.execute(
            select(WorkflowNode).where(WorkflowNode.node_id == target_node_id)
        )
        workflow_nodes = result.scalars().all()
        
        if not workflow_nodes:
            return []
        
        workflow_ids = [wn.workflow_id for wn in workflow_nodes]
        
        workflows_result = await db.execute(
            select(Workflow).where(Workflow.id.in_(workflow_ids))
        )
        workflows = workflows_result.scalars().all()
        
        return [
            WorkflowEvidence(
                id=wf.id,
                name=wf.name,
                workflow_type=wf.workflow_type,
                criticality=wf.criticality,
                confidence=wf.confidence,
                relevance_score=0.9,
            )
            for wf in workflows
        ]
    
    def _empty_response(self, request: ImpactAnalysisRequest) -> ImpactAnalysisResponse:
        """Return empty response when target not found."""
        return ImpactAnalysisResponse(
            intent=request.intent,
            target=request.target,
            target_node_id=None,
            risk_score=RiskScore(
                overall_risk_score=0.0,
                risk_category="unknown",
                confidence=0.0,
                blast_radius_risk=0.0,
                dependency_risk=0.0,
                complexity_risk=0.0,
                workflow_risk=0.0,
                api_risk=0.0,
                database_risk=0.0,
                risk_factors={},
            ),
            blast_radius=BlastRadiusResult(
                total_affected_entities=0,
                direct_dependencies=0,
                indirect_dependencies=0,
                affected_services=[],
                affected_apis=[],
                affected_databases=[],
                affected_functions=[],
                max_depth_reached=0,
                traversal_complete=False,
            ),
            breaking_apis=[],
            breaking_services=[],
            breaking_databases=[],
            affected_services=[],
            affected_databases=[],
            affected_workflows=[],
            engineering_complexity=ComplexityScore(
                overall_score=0.0,
                cyclomatic_complexity=0.0,
                dependency_complexity=0.0,
                coupling_complexity=0.0,
                data_complexity=0.0,
                control_flow_complexity=0.0,
            ),
            migration_difficulty=DifficultyScore(
                overall_score=0.0,
                technical_difficulty=0.0,
                testing_difficulty=0.0,
                deployment_difficulty=0.0,
                migration_difficulty=0.0,
                rollback_difficulty=0.0,
            ),
            implementation_difficulty=DifficultyScore(
                overall_score=0.0,
                technical_difficulty=0.0,
                testing_difficulty=0.0,
                deployment_difficulty=0.0,
                migration_difficulty=0.0,
                rollback_difficulty=0.0,
            ),
            recommended_change_order=[],
            total_estimated_effort_hours=0.0,
            analysis_method="graph_traversal",
            analysis_timestamp=datetime.utcnow().isoformat(),
            nodes_analyzed=0,
            edges_traversed=0,
        )
