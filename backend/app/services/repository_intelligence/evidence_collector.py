"""
Evidence Collectors

Intent-specific strategies for retrieving engineering evidence from the database.
Queries the existing PostgreSQL graph schema without duplicate logic.
"""

from typing import List, Optional, Tuple, Set
from uuid import UUID

from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Node, Edge, Workflow, WorkflowNode
from app.services.repository_intelligence.schemas import (
    EvidenceCategory,
    EvidenceCollection,
    EvidenceItem,
    EdgeEvidenceItem,
    WorkflowEvidenceItem,
)


class EvidenceCollector:
    """Base class for all intent-specific evidence collectors."""

    def __init__(self, repo_id: UUID, target_name: str, target_type: str, max_per_category: int = 25):
        self.repo_id = repo_id
        self.target_name = target_name
        self.target_type = target_type
        self.max_per_category = max_per_category

    async def collect(self, db: AsyncSession) -> EvidenceCollection:
        """Collect intent-specific evidence. Must be implemented by subclasses."""
        raise NotImplementedError

    # -----------------------------------------------------------------------
    # Shared Data Access Methods
    # -----------------------------------------------------------------------

    async def _find_target_nodes(self, db: AsyncSession, limit: int = 5) -> List[Node]:
        """Find the most likely target node(s) based on name/path."""
        stmt = (
            select(Node)
            .where(
                and_(
                    Node.repo_id == self.repo_id,
                    or_(
                        Node.name.ilike(f"%{self.target_name}%"),
                        Node.full_path.ilike(f"%{self.target_name}%"),
                    )
                )
            )
            .order_by(desc(Node.complexity_score))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _get_incoming_edges(self, db: AsyncSession, node_ids: List[UUID]) -> List[Edge]:
        """Find all edges pointing TO the given node IDs."""
        if not node_ids:
            return []
        stmt = select(Edge).where(Edge.to_node_id.in_(node_ids)).limit(self.max_per_category * 2)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _get_outgoing_edges(self, db: AsyncSession, node_ids: List[UUID]) -> List[Edge]:
        """Find all edges pointing FROM the given node IDs."""
        if not node_ids:
            return []
        stmt = select(Edge).where(Edge.from_node_id.in_(node_ids)).limit(self.max_per_category * 2)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _get_nodes_by_ids(self, db: AsyncSession, node_ids: List[UUID]) -> List[Node]:
        """Bulk fetch nodes by their IDs."""
        if not node_ids:
            return []
        unique_ids = list(set(node_ids))
        stmt = select(Node).where(Node.id.in_(unique_ids))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _get_workflows_for_nodes(self, db: AsyncSession, node_ids: List[UUID]) -> List[Workflow]:
        """Find workflows that involve any of the given nodes."""
        if not node_ids:
            return []
        wn_stmt = select(WorkflowNode).where(WorkflowNode.node_id.in_(node_ids))
        wn_result = await db.execute(wn_stmt)
        workflow_ids = [wn.workflow_id for wn in wn_result.scalars().all()]
        
        if not workflow_ids:
            return []
            
        w_stmt = select(Workflow).where(Workflow.id.in_(workflow_ids)).limit(self.max_per_category)
        w_result = await db.execute(w_stmt)
        return list(w_result.scalars().all())
        
    async def _get_nodes_by_type(self, db: AsyncSession, node_type: str, limit: int = None) -> List[Node]:
        """Find highest-complexity nodes of a specific type in the repo."""
        limit = limit or self.max_per_category
        stmt = (
            select(Node)
            .where(
                and_(
                    Node.repo_id == self.repo_id,
                    Node.node_type == node_type
                )
            )
            .order_by(desc(Node.complexity_score))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # Mapping Utilities
    # -----------------------------------------------------------------------

    def _to_evidence_item(self, node: Node, category: EvidenceCategory, distance: int = 1) -> EvidenceItem:
        return EvidenceItem(
            node_id=node.id,
            name=node.name,
            node_type=node.node_type,
            full_path=node.full_path,
            category=category,
            start_line=node.start_line,
            end_line=node.end_line,
            signature=node.signature,
            raw_code=node.raw_code,
            architecture_role=node.architecture_role,
            complexity_score=node.complexity_score,
            is_exported=node.is_exported or False,
            is_async=node.is_async or False,
            relevance_score=0.0,
            graph_distance=distance
        )
        
    def _to_edge_item(self, edge: Edge, from_name: str, to_name: str) -> EdgeEvidenceItem:
        return EdgeEvidenceItem(
            edge_id=edge.id,
            from_node_id=edge.from_node_id,
            from_node_name=from_name,
            to_node_id=edge.to_node_id,
            to_node_name=to_name,
            edge_type=edge.edge_type,
            weight=edge.weight,
            relevance_score=0.0,
        )
        
    def _to_workflow_item(self, workflow: Workflow) -> WorkflowEvidenceItem:
        return WorkflowEvidenceItem(
            workflow_id=workflow.id,
            name=workflow.name,
            workflow_type=workflow.workflow_type,
            criticality=workflow.criticality,
            confidence=workflow.confidence,
            relevance_score=0.0,
        )

    async def _build_neighborhood_evidence(self, db: AsyncSession, target_nodes: List[Node]) -> EvidenceCollection:
        """Common logic to get callers, callees, and workflows for targets."""
        collection = EvidenceCollection()
        
        if not target_nodes:
            return collection
            
        target_ids = [n.id for n in target_nodes]
        
        for node in target_nodes:
            collection.add(EvidenceCategory.REFERENCE, self._to_evidence_item(node, EvidenceCategory.REFERENCE, distance=0))
            
        incoming = await self._get_incoming_edges(db, target_ids)
        outgoing = await self._get_outgoing_edges(db, target_ids)
        
        caller_ids = [e.from_node_id for e in incoming]
        callee_ids = [e.to_node_id for e in outgoing]
        
        related_nodes = await self._get_nodes_by_ids(db, caller_ids + callee_ids)
        node_lookup = {n.id: n for n in related_nodes}
        
        for edge in incoming:
            if edge.from_node_id in node_lookup:
                caller = node_lookup[edge.from_node_id]
                collection.add(EvidenceCategory.CALLER, self._to_evidence_item(caller, EvidenceCategory.CALLER, distance=1))
                target = next((n for n in target_nodes if n.id == edge.to_node_id), None)
                target_name = target.name if target else str(edge.to_node_id)
                collection.add_edge(self._to_edge_item(edge, caller.name, target_name))
                
        for edge in outgoing:
            if edge.to_node_id in node_lookup:
                callee = node_lookup[edge.to_node_id]
                collection.add(EvidenceCategory.CALLEE, self._to_evidence_item(callee, EvidenceCategory.CALLEE, distance=1))
                target = next((n for n in target_nodes if n.id == edge.from_node_id), None)
                target_name = target.name if target else str(edge.from_node_id)
                collection.add_edge(self._to_edge_item(edge, target_name, callee.name))
                
        workflows = await self._get_workflows_for_nodes(db, target_ids)
        for wf in workflows:
            collection.add_workflow(self._to_workflow_item(wf))
            
        return collection


# ---------------------------------------------------------------------------
# Intent-Specific Collectors
# ---------------------------------------------------------------------------

class DeleteEvidenceCollector(EvidenceCollector):
    async def collect(self, db: AsyncSession) -> EvidenceCollection:
        targets = await self._find_target_nodes(db)
        return await self._build_neighborhood_evidence(db, targets)


class AddFeatureEvidenceCollector(EvidenceCollector):
    async def collect(self, db: AsyncSession) -> EvidenceCollection:
        collection = EvidenceCollection()
        similar = await self._find_target_nodes(db, limit=5)
        for node in similar:
            collection.add(EvidenceCategory.PATTERN, self._to_evidence_item(node, EvidenceCategory.PATTERN, distance=0))
            
        services = await self._get_nodes_by_type(db, "service", limit=10)
        for svc in services:
            collection.add(EvidenceCategory.INTEGRATION_POINT, self._to_evidence_item(svc, EvidenceCategory.INTEGRATION_POINT, distance=1))
            
        apis = await self._get_nodes_by_type(db, "api_route", limit=5)
        for api in apis:
            collection.add(EvidenceCategory.API, self._to_evidence_item(api, EvidenceCategory.API, distance=1))
            
        models = await self._get_nodes_by_type(db, "model", limit=5)
        for model in models:
            collection.add(EvidenceCategory.DATABASE, self._to_evidence_item(model, EvidenceCategory.DATABASE, distance=1))
            
        return collection


class ExplainEvidenceCollector(EvidenceCollector):
    async def collect(self, db: AsyncSession) -> EvidenceCollection:
        targets = await self._find_target_nodes(db)
        collection = await self._build_neighborhood_evidence(db, targets)
        
        for item in collection.get(EvidenceCategory.CALLER) + collection.get(EvidenceCategory.CALLEE):
            if item.architecture_role:
                collection.add(EvidenceCategory.ARCHITECTURE, item)
                
        return collection


class RenameEvidenceCollector(EvidenceCollector):
    async def collect(self, db: AsyncSession) -> EvidenceCollection:
        return await DeleteEvidenceCollector(
            self.repo_id, self.target_name, self.target_type, self.max_per_category
        ).collect(db)


class RefactorEvidenceCollector(EvidenceCollector):
    async def collect(self, db: AsyncSession) -> EvidenceCollection:
        targets = await self._find_target_nodes(db)
        return await self._build_neighborhood_evidence(db, targets)


class DependencyEvidenceCollector(EvidenceCollector):
    async def collect(self, db: AsyncSession) -> EvidenceCollection:
        targets = await self._find_target_nodes(db)
        collection = await self._build_neighborhood_evidence(db, targets)
        
        callers = collection.items.pop(EvidenceCategory.CALLER.value, [])
        for c in callers:
            c.category = EvidenceCategory.DEPENDENT
            collection.add(EvidenceCategory.DEPENDENT, c)
            
        callees = collection.items.pop(EvidenceCategory.CALLEE.value, [])
        for c in callees:
            c.category = EvidenceCategory.DEPENDENCY
            collection.add(EvidenceCategory.DEPENDENCY, c)
            
        return collection


class ArchitectureEvidenceCollector(EvidenceCollector):
    async def collect(self, db: AsyncSession) -> EvidenceCollection:
        collection = EvidenceCollection()
        
        services = await self._get_nodes_by_type(db, "service", limit=self.max_per_category)
        apis = await self._get_nodes_by_type(db, "api_route", limit=self.max_per_category)
        
        for svc in services:
            collection.add(EvidenceCategory.ARCHITECTURE, self._to_evidence_item(svc, EvidenceCategory.ARCHITECTURE, distance=1))
            
        for api in apis:
            collection.add(EvidenceCategory.API, self._to_evidence_item(api, EvidenceCategory.API, distance=1))
            
        return collection


class PlanningEvidenceCollector(EvidenceCollector):
    async def collect(self, db: AsyncSession) -> EvidenceCollection:
        return await AddFeatureEvidenceCollector(
            self.repo_id, self.target_name, self.target_type, self.max_per_category
        ).collect(db)


class UnknownEvidenceCollector(EvidenceCollector):
    async def collect(self, db: AsyncSession) -> EvidenceCollection:
        collection = EvidenceCollection()
        targets = await self._find_target_nodes(db, limit=5)
        for t in targets:
            collection.add(EvidenceCategory.REFERENCE, self._to_evidence_item(t, EvidenceCategory.REFERENCE, distance=0))
        return collection
