"""Repository Data Collector - Collects structured repository data for AI reasoning."""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Node, Edge
from .models import (
    ASTNode, DependencyGraph, DependencyEdge, CallGraph,
    ClassInfo, FunctionInfo, APIRoute, ImportInfo
)

logger = logging.getLogger(__name__)

class RepositoryDataCollector:
    """
    Collects structured repository data for AI reasoning.
    
    This service ensures all AI responses are grounded in repository data by:
    - Collecting AST information from source code
    - Building dependency graphs from database edges
    - Extracting call graphs
    - Cataloging classes and functions
    - Identifying API routes
    - Tracking imports
    
    Never fabricates dependencies - only reports what exists in the repository.
    """
    
    def __init__(self):
        """Initialize the repository data collector."""
    
    async def collect_repository_data(
        self,
        repo_id: UUID,
        repo_path: str,
        target_name: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Collect all structured repository data.
        
        Args:
            repo_id: Repository UUID
            repo_path: Path to repository
            target_name: Optional target name (unused here, kept for backwards compatibility)
            db: Database session for node queries
            
        Returns:
            Dictionary containing all collected data types
        """
        logger.info(f"Collecting repository data for repo {repo_id}")
        
        data = {
            'ast_nodes': [],
            'dependency_graph': None,
            'call_graph': None,
            'classes': [],
            'functions': [],
            'api_routes': [],
            'imports': []
        }
        
        if db:
            data['ast_nodes'] = await self._collect_ast_nodes_from_db(repo_id, db)
            data['classes'] = await self._collect_classes_from_db(repo_id, db)
            data['functions'] = await self._collect_functions_from_db(repo_id, db)
            data['api_routes'] = await self._collect_api_routes_from_db(repo_id, db)
            data['imports'] = await self._collect_imports_from_db(repo_id, db)
            data['dependency_graph'] = await self._collect_dependency_graph_from_db(repo_id, db)
        
        # Build call graph from function data
        data['call_graph'] = self._build_call_graph(data['functions'])
        
        # Calculate completeness
        total_types = 5
        counts = [
            len(data['ast_nodes']),
            len(data['classes']),
            len(data['functions']),
            len(data['api_routes']),
            len(data['imports'])
        ]
        non_zero = sum(1 for c in counts if c > 0)
        avg_completeness = (non_zero / total_types) * 100 if total_types > 0 else 0
        
        logger.info("Repository data collection complete:")
        logger.info(f"  - Total Nodes (AST): {len(data['ast_nodes'])}")
        logger.info(f"  - Classes: {len(data['classes'])}")
        logger.info(f"  - Functions: {len(data['functions'])}")
        logger.info(f"  - API routes: {len(data['api_routes'])}")
        logger.info(f"  - Imports: {len(data['imports'])}")
        logger.info(f"  - Dependency edges: {len(data['dependency_graph'].edges) if data['dependency_graph'] else 0}")
        logger.info(f"  - Call graph entries: {len(data['call_graph'].function_calls) if data['call_graph'] else 0}")
        logger.info(f"  - Average completeness: {avg_completeness:.1f}%")
        
        return data

    def _get_node_file_path(self, node: Node) -> str:
        """Safely extract file path from a Node."""
        full_path = getattr(node, "full_path", None)
        if full_path:
            return full_path.split(":")[0]
        return "unknown"
    
    async def _collect_ast_nodes_from_db(
        self,
        repo_id: UUID,
        db: AsyncSession
    ) -> List[ASTNode]:
        """Collect AST nodes from database."""
        try:
            query = select(Node).where(Node.repo_id == repo_id)
            result = await db.execute(query)
            nodes = result.scalars().all()
            
            ast_nodes = []
            for node in nodes:
                try:
                    ast_node = ASTNode(
                        node_type=getattr(node, "node_type", "unknown") or "unknown",
                        name=getattr(node, "name", "unknown"),
                        file_path=self._get_node_file_path(node),
                        line_number=getattr(node, "start_line", 0) or 0,
                        parent=None,
                        children=[],
                        metadata={
                            'node_id': str(getattr(node, "id", "")),
                            'end_line': getattr(node, "end_line", None),
                        }
                    )
                    ast_nodes.append(ast_node)
                except Exception as parse_err:
                    logger.warning(f"Failed to parse AST node (id={getattr(node, 'id', 'unknown')}): {parse_err}")
                    continue
            
            return ast_nodes
        except Exception as e:
            logger.error(f"Error collecting AST nodes from DB: {e}")
            return []
    
    async def _collect_classes_from_db(
        self,
        repo_id: UUID,
        db: AsyncSession
    ) -> List[ClassInfo]:
        """Collect class information from database."""
        try:
            query = select(Node).where(
                Node.repo_id == repo_id,
                Node.node_type == "class"
            )
            result = await db.execute(query)
            nodes = result.scalars().all()
            
            classes = []
            for node in nodes:
                try:
                    class_info = ClassInfo(
                        name=getattr(node, "name", "unknown"),
                        file_path=self._get_node_file_path(node),
                        line_number=getattr(node, "start_line", 0) or 0,
                        methods=[],
                        attributes=[],
                        base_classes=[],
                        derived_classes=[]
                    )
                    classes.append(class_info)
                except Exception as parse_err:
                    logger.warning(f"Failed to parse class node (id={getattr(node, 'id', 'unknown')}): {parse_err}")
                    continue
            
            return classes
        except Exception as e:
            logger.error(f"Error collecting classes from DB: {e}")
            return []
    
    async def _collect_functions_from_db(
        self,
        repo_id: UUID,
        db: AsyncSession
    ) -> List[FunctionInfo]:
        """Collect function information from database."""
        try:
            query = select(Node).where(
                Node.repo_id == repo_id,
                Node.node_type.in_(["function", "method"])
            )
            result = await db.execute(query)
            nodes = result.scalars().all()
            
            functions = []
            for node in nodes:
                try:
                    function_info = FunctionInfo(
                        name=getattr(node, "name", "unknown"),
                        file_path=self._get_node_file_path(node),
                        line_number=getattr(node, "start_line", 0) or 0,
                        parameters=[],
                        return_type=None,
                        calls=getattr(node, "calls", []) or [],
                        called_by=getattr(node, "called_by", []) or []
                    )
                    functions.append(function_info)
                except Exception as parse_err:
                    logger.warning(f"Failed to parse function node (id={getattr(node, 'id', 'unknown')}): {parse_err}")
                    continue
            
            return functions
        except Exception as e:
            logger.error(f"Error collecting functions from DB: {e}")
            return []
    
    async def _collect_api_routes_from_db(
        self,
        repo_id: UUID,
        db: AsyncSession
    ) -> List[APIRoute]:
        """Collect API route information from database."""
        try:
            query = select(Node).where(
                Node.repo_id == repo_id,
                Node.node_type.in_(["api_route", "route", "endpoint"])
            )
            result = await db.execute(query)
            nodes = result.scalars().all()
            
            routes = []
            for node in nodes:
                try:
                    route_info = APIRoute(
                        path=getattr(node, "route_path", None) or getattr(node, "name", "unknown"),
                        method=getattr(node, "http_method", None) or "GET",
                        handler=getattr(node, "name", "unknown"),
                        file_path=self._get_node_file_path(node),
                        line_number=getattr(node, "start_line", 0) or 0,
                        middleware=[]
                    )
                    routes.append(route_info)
                except Exception as parse_err:
                    logger.warning(f"Failed to parse API route node (id={getattr(node, 'id', 'unknown')}): {parse_err}")
                    continue
            
            return routes
        except Exception as e:
            logger.error(f"Error collecting API routes from DB: {e}")
            return []
    
    async def _collect_imports_from_db(
        self,
        repo_id: UUID,
        db: AsyncSession
    ) -> List[ImportInfo]:
        """Collect import information from database."""
        try:
            query = select(Node).where(
                Node.repo_id == repo_id,
                Node.node_type == "import"
            )
            result = await db.execute(query)
            nodes = result.scalars().all()
            
            imports = []
            for node in nodes:
                try:
                    import_info = ImportInfo(
                        module=getattr(node, "name", "unknown"),
                        alias=None,
                        file_path=self._get_node_file_path(node),
                        line_number=getattr(node, "start_line", 0) or 0,
                        import_type="direct_import"
                    )
                    imports.append(import_info)
                except Exception as parse_err:
                    logger.warning(f"Failed to parse import node (id={getattr(node, 'id', 'unknown')}): {parse_err}")
                    continue
            
            return imports
        except Exception as e:
            logger.error(f"Error collecting imports from DB: {e}")
            return []
            
    async def _collect_dependency_graph_from_db(
        self,
        repo_id: UUID,
        db: AsyncSession
    ) -> DependencyGraph:
        """Build dependency graph directly from Edge table."""
        try:
            # Get all nodes in repo to build node_map
            node_result = await db.execute(
                select(Node.id, Node.name, Node.full_path).where(Node.repo_id == repo_id)
            )
            node_map = {}
            nodes_set = set()
            for row in node_result.all():
                node_map[row[0]] = (row[1], row[2])
                nodes_set.add(row[1])
                
            # Get all edges for repo
            edge_result = await db.execute(
                select(Edge).where(Edge.repo_id == repo_id)
            )
            edges_db = edge_result.scalars().all()
            
            dependency_edges = []
            for edge in edges_db:
                from_info = node_map.get(edge.from_node_id, ("unknown", None))
                to_info = node_map.get(edge.to_node_id, ("unknown", None))
                
                from_name = from_info[0]
                to_name = to_info[0]
                
                # Only add if valid names
                if from_name != "unknown" and to_name != "unknown":
                    full_path = from_info[1]
                    file_path = full_path.split(":")[0] if full_path else "unknown"
                    
                    dep_edge = DependencyEdge(
                        from_node=from_name,
                        to_node=to_name,
                        edge_type=edge.edge_type or "dependency",
                        confidence=edge.weight or 0.9,
                        file_path=file_path
                    )
                    dependency_edges.append(dep_edge)
                    
            return DependencyGraph(
                nodes=list(nodes_set),
                edges=dependency_edges,
                total_nodes=len(nodes_set),
                total_edges=len(dependency_edges)
            )
            
        except Exception as e:
            logger.error(f"Error collecting dependency graph from DB: {e}")
            return DependencyGraph(nodes=[], edges=[], total_nodes=0, total_edges=0)
    
    def _build_call_graph(self, functions: List[FunctionInfo]) -> CallGraph:
        """Build call graph from function information."""
        function_calls = []
        entry_points = []
        
        for func in functions:
            for called_func in func.calls:
                function_calls.append({
                    'from': func.name,
                    'to': called_func,
                    'file_path': func.file_path
                })
            
            if any(entry in func.name.lower() for entry in ['main', 'run', 'start', 'init', 'handler']):
                entry_points.append(func.name)
        
        return CallGraph(
            function_calls=function_calls,
            call_depth=0,
            entry_points=entry_points
        )
    
    def validate_dependencies(
        self,
        dependency_graph: DependencyGraph,
        allowed_nodes: Optional[List[str]] = None
    ) -> List[str]:
        """Validate that all dependencies are grounded in repository data."""
        errors = []
        
        if not allowed_nodes:
            allowed_nodes = dependency_graph.nodes
        
        for edge in dependency_graph.edges:
            if edge.to_node not in allowed_nodes and not edge.to_node.startswith('.'):
                errors.append(f"Dependency to unknown node: {edge.to_node}")
        
        return errors
