from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Node, Edge, Workflow, WorkflowNode
from app.models.intent import Intent
from app.schemas.evidence import (
    EvidenceRequest,
    EvidenceResponse,
    NodeEvidence,
    WorkflowEvidence,
)


class EvidenceCollector:
    """Base class for intent-specific evidence collection strategies."""
    
    def __init__(self, repo_id: UUID, target: str, max_results: int = 50):
        self.repo_id = repo_id
        self.target = target
        self.max_results = max_results
    
    async def collect(self, db: AsyncSession) -> EvidenceResponse:
        """Collect evidence. Must be implemented by subclasses."""
        raise NotImplementedError


class DeleteCodeEvidenceCollector(EvidenceCollector):
    """Evidence collector for DELETE_CODE intent."""
    
    async def collect(self, db: AsyncSession) -> EvidenceResponse:
        """Collect evidence for delete operations."""
        # Find the target node
        target_node = await self._find_target_node(db)
        if not target_node:
            return self._empty_response()
        
        # Collect evidence in parallel
        (
            affected_functions,
            affected_services,
            affected_apis,
            affected_db_tables,
            callers,
            callees,
            imports,
            dependencies,
            dependents,
            critical_paths,
            workflows,
        ) = await self._collect_all_evidence(target_node, db)
        
        # Build response
        return EvidenceResponse(
            intent=Intent.DELETE_CODE,
            target=self.target,
            target_node=self._to_node_evidence(target_node, relevance_score=1.0),
            affected_functions=affected_functions,
            affected_services=affected_services,
            affected_apis=affected_apis,
            affected_database_tables=affected_db_tables,
            callers=callers,
            callees=callees,
            imports=imports,
            dependencies=dependencies,
            dependents=dependents,
            critical_paths=critical_paths,
            workflows=workflows,
            total_nodes_analyzed=len(affected_functions) + len(affected_services) + len(affected_apis),
            collection_method="graph_traversal",
            confidence=0.9,
        )
    
    async def _find_target_node(self, db: AsyncSession) -> Optional[Node]:
        """Find the target node by name."""
        result = await db.execute(
            select(Node)
            .where(
                and_(
                    Node.repo_id == self.repo_id,
                    or_(
                        Node.name.ilike(f"%{self.target}%"),
                        Node.full_path.ilike(f"%{self.target}%"),
                    )
                )
            )
            .order_by(Node.complexity_score.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _collect_all_evidence(
        self, target_node: Node, db: AsyncSession
    ) -> tuple:
        """Collect all evidence types."""
        # Get edges for this node
        incoming_edges_result = await db.execute(
            select(Edge).where(Edge.to_node_id == target_node.id)
        )
        outgoing_edges_result = await db.execute(
            select(Edge).where(Edge.from_node_id == target_node.id)
        )
        
        incoming_edges = incoming_edges_result.scalars().all()
        outgoing_edges = outgoing_edges_result.scalars().all()
        
        # Get caller and callee node IDs
        caller_ids = [e.from_node_id for e in incoming_edges]
        callee_ids = [e.to_node_id for e in outgoing_edges]
        
        # Fetch related nodes
        callers_nodes = await self._fetch_nodes_by_ids(caller_ids, db)
        callees_nodes = await self._fetch_nodes_by_ids(callee_ids, db)
        
        # Categorize nodes by type
        affected_functions = self._filter_by_type(callers_nodes + callees_nodes, "function")
        affected_services = self._filter_by_type(callers_nodes + callees_nodes, "service")
        affected_apis = self._filter_by_type(callers_nodes + callees_nodes, "api_route")
        affected_db_tables = self._filter_by_type(callers_nodes + callees_nodes, "model")
        
        # Rank and limit
        affected_functions = self._rank_and_limit(affected_functions, target_node)
        affected_services = self._rank_and_limit(affected_services, target_node)
        affected_apis = self._rank_and_limit(affected_apis, target_node)
        affected_db_tables = self._rank_and_limit(affected_db_tables, target_node)
        
        # Separate callers and callees
        callers = self._rank_and_limit(callers_nodes, target_node)
        callees = self._rank_and_limit(callees_nodes, target_node)
        
        # Get imports
        imports = target_node.imports if target_node.imports else []
        
        # Dependencies (nodes that target depends on)
        dependencies = self._rank_and_limit(callees_nodes, target_node)
        
        # Dependents (nodes that depend on target)
        dependents = self._rank_and_limit(callers_nodes, target_node)
        
        # Critical paths (simplified - just high-weight paths)
        critical_paths = await self._find_critical_paths(target_node, db)
        
        # Workflows
        workflows = await self._find_related_workflows(target_node, db)
        
        return (
            affected_functions,
            affected_services,
            affected_apis,
            affected_db_tables,
            callers,
            callees,
            imports,
            dependencies,
            dependents,
            critical_paths,
            workflows,
        )
    
    async def _fetch_nodes_by_ids(self, node_ids: List[UUID], db: AsyncSession) -> List[Node]:
        """Fetch nodes by IDs."""
        if not node_ids:
            return []
        result = await db.execute(
            select(Node).where(Node.id.in_(node_ids))
        )
        return list(result.scalars().all())
    
    def _filter_by_type(self, nodes: List[Node], node_type: str) -> List[Node]:
        """Filter nodes by type."""
        return [n for n in nodes if n.node_type == node_type]
    
    def _rank_and_limit(self, nodes: List[Node], target_node: Node) -> List[NodeEvidence]:
        """Rank nodes by relevance and limit results."""
        if not nodes:
            return []
        
        # Calculate relevance scores
        scored = []
        for node in nodes:
            relevance = self._calculate_relevance(node, target_node)
            scored.append((node, relevance))
        
        # Sort by relevance
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        limited = scored[:self.max_results]
        
        # Convert to evidence
        return [self._to_node_evidence(node, score) for node, score in limited]
    
    def _calculate_relevance(self, node: Node, target_node: Node) -> float:
        """Calculate relevance score for a node."""
        score = 0.0
        
        # Same file = higher relevance
        if node.file_id == target_node.file_id:
            score += 0.3
        
        # Similar name = higher relevance
        if node.name.lower() in target_node.name.lower() or target_node.name.lower() in node.name.lower():
            score += 0.2
        
        # Complexity correlation
        score += min(node.complexity_score / 10.0, 0.2)
        
        # Architecture role match
        if node.architecture_role == target_node.architecture_role:
            score += 0.1
        
        # Type-specific bonuses
        if node.node_type == target_node.node_type:
            score += 0.2
        
        return min(score, 1.0)
    
    def _to_node_evidence(self, node: Node, relevance_score: float) -> NodeEvidence:
        """Convert Node to NodeEvidence."""
        return NodeEvidence(
            id=node.id,
            name=node.name,
            node_type=node.node_type,
            full_path=node.full_path,
            signature=node.signature,
            raw_code=node.raw_code,
            start_line=node.start_line,
            end_line=node.end_line,
            complexity_score=node.complexity_score,
            architecture_role=node.architecture_role,
            relevance_score=relevance_score,
        )
    
    async def _find_critical_paths(self, target_node: Node, db: AsyncSession) -> List[List[NodeEvidence]]:
        """Find critical paths through the target node."""
        # Simplified: get high-weight incoming/outgoing edges
        incoming_result = await db.execute(
            select(Edge)
            .where(and_(Edge.to_node_id == target_node.id, Edge.weight > 0.5))
            .order_by(Edge.weight.desc())
            .limit(5)
        )
        outgoing_result = await db.execute(
            select(Edge)
            .where(and_(Edge.from_node_id == target_node.id, Edge.weight > 0.5))
            .order_by(Edge.weight.desc())
            .limit(5)
        )
        
        incoming_edges = incoming_result.scalars().all()
        outgoing_edges = outgoing_result.scalars().all()
        
        paths = []
        
        # Build paths from incoming -> target -> outgoing
        for in_edge in incoming_edges:
            for out_edge in outgoing_edges:
                from_node = await self._fetch_nodes_by_ids([in_edge.from_node_id], db)
                to_node = await self._fetch_nodes_by_ids([out_edge.to_node_id], db)
                
                if from_node and to_node:
                    path = [
                        self._to_node_evidence(from_node[0], 0.8),
                        self._to_node_evidence(target_node, 1.0),
                        self._to_node_evidence(to_node[0], 0.8),
                    ]
                    paths.append(path)
        
        return paths[:3]  # Limit to top 3 paths
    
    async def _find_related_workflows(self, target_node: Node, db: AsyncSession) -> List[WorkflowEvidence]:
        """Find workflows that include this node."""
        result = await db.execute(
            select(WorkflowNode)
            .where(WorkflowNode.node_id == target_node.id)
        )
        workflow_nodes = result.scalars().all()
        
        if not workflow_nodes:
            return []
        
        workflow_ids = [wn.workflow_id for wn in workflow_nodes]
        
        workflows_result = await db.execute(
            select(Workflow).where(Workflow.id.in_(workflow_ids))
        )
        workflows = workflows_result.scalars().all()
        
        evidence_list = []
        for wf in workflows:
            evidence_list.append(
                WorkflowEvidence(
                    id=wf.id,
                    name=wf.name,
                    workflow_type=wf.workflow_type,
                    criticality=wf.criticality,
                    confidence=wf.confidence,
                    relevance_score=0.8,
                )
            )
        
        return evidence_list[:self.max_results]
    
    def _empty_response(self) -> EvidenceResponse:
        """Return empty response when target not found."""
        return EvidenceResponse(
            intent=Intent.DELETE_CODE,
            target=self.target,
            target_node=None,
            collection_method="graph_traversal",
            confidence=0.0,
        )


class AddFeatureEvidenceCollector(EvidenceCollector):
    """Evidence collector for ADD_FEATURE intent."""
    
    async def collect(self, db: AsyncSession) -> EvidenceResponse:
        """Collect evidence for add feature operations."""
        # For ADD_FEATURE, we want to find similar existing features
        # and relevant integration points
        
        # Find nodes with similar names
        similar_nodes_result = await db.execute(
            select(Node)
            .where(
                and_(
                    Node.repo_id == self.repo_id,
                    Node.name.ilike(f"%{self.target}%")
                )
            )
            .order_by(Node.complexity_score.desc())
            .limit(self.max_results)
        )
        similar_nodes = similar_nodes_result.scalars().all()
        
        # Find service nodes (good integration points)
        services_result = await db.execute(
            select(Node)
            .where(
                and_(
                    Node.repo_id == self.repo_id,
                    Node.node_type == "service"
                )
            )
            .order_by(Node.complexity_score.desc())
            .limit(self.max_results)
        )
        services = services_result.scalars().all()
        
        # Find API routes
        apis_result = await db.execute(
            select(Node)
            .where(
                and_(
                    Node.repo_id == self.repo_id,
                    Node.node_type == "api_route"
                )
            )
            .order_by(Node.complexity_score.desc())
            .limit(self.max_results)
        )
        apis = apis_result.scalars().all()
        
        return EvidenceResponse(
            intent=Intent.ADD_FEATURE,
            target=self.target,
            target_node=None,
            affected_services=[self._to_node_evidence(s, 0.7) for s in services],
            affected_apis=[self._to_node_evidence(a, 0.7) for a in apis],
            affected_functions=[self._to_node_evidence(n, 0.6) for n in similar_nodes],
            total_nodes_analyzed=len(similar_nodes) + len(services) + len(apis),
            collection_method="semantic_search",
            confidence=0.75,
        )
    
    def _to_node_evidence(self, node: Node, relevance_score: float) -> NodeEvidence:
        """Convert Node to NodeEvidence."""
        return NodeEvidence(
            id=node.id,
            name=node.name,
            node_type=node.node_type,
            full_path=node.full_path,
            signature=node.signature,
            raw_code=node.raw_code,
            start_line=node.start_line,
            end_line=node.end_line,
            complexity_score=node.complexity_score,
            architecture_role=node.architecture_role,
            relevance_score=relevance_score,
        )


class RepositoryEvidenceEngine:
    """
    Main Repository Evidence Engine service.
    
    This engine collects repository evidence before any AI generation.
    It receives intent, repository ID, and target, then retrieves only
    relevant graph information ranked by relevance.
    """
    
    def __init__(self):
        self._collectors = {
            Intent.DELETE_CODE: DeleteCodeEvidenceCollector,
            Intent.ADD_FEATURE: AddFeatureEvidenceCollector,
            # Add more collectors as needed
        }
    
    async def collect_evidence(self, request: EvidenceRequest, db: AsyncSession) -> EvidenceResponse:
        """
        Collect evidence based on intent and target.
        
        Args:
            request: Evidence request with intent, repo_id, target
            db: Database session
            
        Returns:
            EvidenceResponse with ranked and limited evidence
        """
        # Get appropriate collector
        collector_class = self._collectors.get(request.intent)
        
        if not collector_class:
            # Default to generic collection
            return await self._generic_collection(request, db)
        
        # Create collector and collect evidence
        collector = collector_class(
            repo_id=request.repo_id,
            target=request.target,
            max_results=request.max_results
        )
        
        return await collector.collect(db)
    
    async def _generic_collection(self, request: EvidenceRequest, db: AsyncSession) -> EvidenceResponse:
        """Generic evidence collection for unsupported intents."""
        # Find target node
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
            .limit(request.max_results)
        )
        nodes = result.scalars().all()
        
        return EvidenceResponse(
            intent=request.intent,
            target=request.target,
            target_node=self._to_node_evidence(nodes[0], 1.0) if nodes else None,
            affected_functions=[self._to_node_evidence(n, 0.5) for n in nodes[:request.max_results]],
            total_nodes_analyzed=len(nodes),
            collection_method="generic_search",
            confidence=0.5,
        )
    
    def _to_node_evidence(self, node: Node, relevance_score: float) -> NodeEvidence:
        """Convert Node to NodeEvidence."""
        return NodeEvidence(
            id=node.id,
            name=node.name,
            node_type=node.node_type,
            full_path=node.full_path,
            signature=node.signature,
            raw_code=node.raw_code,
            start_line=node.start_line,
            end_line=node.end_line,
            complexity_score=node.complexity_score,
            architecture_role=node.architecture_role,
            relevance_score=relevance_score,
        )
