"""Engineering Evidence Engine - Pipeline Integration."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func

from app.models import Node, Edge, Repo
from app.services.reference_intelligence.reference_intelligence_engine import ReferenceIntelligenceEngine
from app.services.reference_intelligence.models import ReferenceAnalysisResult, Criticality
from .engineering_evidence_engine import EngineeringEvidenceEngine
from .models import EngineeringEvidence
from .repository_data_collector import RepositoryDataCollector

logger = logging.getLogger(__name__)


class EngineeringEvidenceService:
    """
    Service for integrating Engineering Evidence Engine into the pipeline.
    
    This service orchestrates:
    1. Repository Data Collector (collects AST, dependency graph, call graph, classes, functions, API routes, imports)
    2. Reference Intelligence Engine (finds references — requires filesystem access)
    3. Engineering Evidence Engine (explains why references matter)
    
    Output: EngineeringEvidence (single source of truth for engineering decisions)
    
    All AI responses must be grounded in this repository evidence.
    
    Repository Storage Architecture:
    - Repositories are cloned temporarily during initial analysis (analysis.py).
    - After analysis, all structured data (nodes, edges, files) is persisted to PostgreSQL.
    - The clone is then deleted — no `clone_path` column exists on the Repo model.
    - At query time, evidence is collected from the database, NOT the filesystem.
    - Reference Intelligence Engine (filesystem-based) runs only when a local clone exists.
    """
    
    def __init__(self):
        self.data_collector = RepositoryDataCollector()
        self.reference_engine = ReferenceIntelligenceEngine()
        self.evidence_engine = EngineeringEvidenceEngine()
    
    async def generate_evidence(
        self,
        repo_id: UUID,
        target_name: str,
        target_id: Optional[UUID] = None,
        target_type: str = "unknown",
        repo_path: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> EngineeringEvidence:
        """
        Generate engineering evidence for a target.
        
        Args:
            repo_id: Repository UUID
            target_name: Name of the target entity
            target_id: UUID of the target entity (optional, will resolve if not provided)
            target_type: Type of the target entity
            repo_path: Path to repository (optional, will fetch from DB if not provided)
            db: Database session (optional, for resolving target_id and repo_path)
            
        Returns:
            EngineeringEvidence with structured evidence grounded in repository data
        """
        logger.info("=" * 60)
        logger.info("ENGINEERING EVIDENCE — START")
        logger.info(f"  repo_id:     {repo_id}")
        logger.info(f"  target_name: {target_name}")
        logger.info(f"  target_type: {target_type}")
        logger.info(f"  repo_path:   {repo_path or '(not provided — will resolve)'}")
        logger.info("=" * 60)

        # ── Step 0: Validate repository exists in database ──
        if db:
            repo_valid = await self._validate_repository(repo_id, db)
            if not repo_valid:
                logger.error(f"Repository {repo_id} not found in database")
                return self._error_evidence(
                    repo_id, target_name, target_type,
                    reason="Repository not found in database"
                )
        
        # ── Step 1: Resolve target_id ──
        target_resolved = True
        if target_id is None and db:
            target_id = await self._resolve_target_id(repo_id, target_name, db)
        
        if target_id is None:
            logger.warning(
                f"Could not resolve target_id for '{target_name}' — "
                f"using repo_id as fallback. Evidence will be collected via "
                f"text-based reference search."
            )
            target_id = repo_id
            target_resolved = False
        else:
            logger.info(f"Resolved target_id: {target_id}")
        
        # ── Step 2: Resolve repo_path ──
        if repo_path is None and db:
            repo_path = await self._resolve_repo_path(repo_id, db)
        
        # Check whether the filesystem path actually exists
        repo_on_disk = repo_path is not None and Path(repo_path).is_dir()
        logger.info(f"Resolved repo path: {repo_path or '(virtual — DB only)'}")
        logger.info(f"Repo on disk: {repo_on_disk}")
        
        # ── Step 3: Repository Data Collection (from DB — always available) ──
        logger.info("Collecting repository data from database...")
        repository_data = await self.data_collector.collect_repository_data(
            repo_id=repo_id,
            repo_path=repo_path or f"virtual://{repo_id}",
            target_name=target_name,
            db=db
        )
        
        # Log collected data
        logger.info("Loaded AST: %d nodes", len(repository_data.get('ast_nodes', [])))
        logger.info("Loaded dependency graph: %d edges",
                     len(repository_data['dependency_graph'].edges) if repository_data.get('dependency_graph') else 0)
        logger.info("Loaded classes: %d", len(repository_data.get('classes', [])))
        logger.info("Loaded functions: %d", len(repository_data.get('functions', [])))
        logger.info("Loaded API routes: %d", len(repository_data.get('api_routes', [])))
        logger.info("Loaded imports: %d", len(repository_data.get('imports', [])))
        
        # ── Step 3b: Enrich dependency graph from Edge table ──
        if db:
            db_edges = await self._collect_edges_from_db(repo_id, target_name, db)
            if db_edges and repository_data.get('dependency_graph'):
                from .models import DependencyEdge
                for edge_data in db_edges:
                    dep_edge = DependencyEdge(
                        from_node=edge_data['from_name'],
                        to_node=edge_data['to_name'],
                        edge_type=edge_data['edge_type'],
                        confidence=edge_data['weight'],
                        file_path=edge_data.get('file_path')
                    )
                    repository_data['dependency_graph'].edges.append(dep_edge)
                repository_data['dependency_graph'].total_edges = len(repository_data['dependency_graph'].edges)
                logger.info("Enriched dependency graph with %d DB edges (total: %d)",
                           len(db_edges), repository_data['dependency_graph'].total_edges)
        
        # ── Step 4: Reference Intelligence (filesystem-based — optional) ──
        reference_analysis = None
        if repo_on_disk:
            logger.info("Running Reference Intelligence (filesystem available)...")
            try:
                reference_analysis = await self.reference_engine.analyze_references(
                    repo_id=repo_id,
                    repo_path=repo_path,
                    target_name=target_name,
                    target_id=target_id,
                    target_type=target_type,
                    max_depth=5,
                    include_tests=True,
                    include_infrastructure=True,
                    include_configuration=True
                )
                logger.info("Loaded references: %d", reference_analysis.total_references)
            except Exception as e:
                logger.warning(f"Reference Intelligence failed (non-fatal): {e}")
                reference_analysis = None
        else:
            logger.info(
                "Reference Intelligence SKIPPED — repository not on disk. "
                "Evidence will be derived from database nodes and edges only."
            )
        
        # ── Step 5: Build Engineering Evidence ──
        if reference_analysis and reference_analysis.total_references > 0:
            # Full path: transform references into structured evidence
            logger.info("Running Engineering Evidence Engine (from references)...")
            engineering_evidence = self.evidence_engine.transform_references_to_evidence(
                reference_analysis
            )
        else:
            # DB-only path: create evidence directly from repository data
            logger.info("Building Engineering Evidence from database data...")
            engineering_evidence = self._build_evidence_from_db_data(
                repo_id=repo_id,
                target_id=target_id,
                target_name=target_name,
                target_type=target_type,
                repository_data=repository_data,
            )
        
        # ── Step 6: Enrich with repository structure data ──
        engineering_evidence.ast_nodes = repository_data.get('ast_nodes', [])
        engineering_evidence.dependency_graph = repository_data.get('dependency_graph')
        engineering_evidence.call_graph = repository_data.get('call_graph')
        engineering_evidence.classes = repository_data.get('classes', [])
        engineering_evidence.functions = repository_data.get('functions', [])
        engineering_evidence.api_routes = repository_data.get('api_routes', [])
        engineering_evidence.imports = repository_data.get('imports', [])
        
        # ── Step 7: Validate dependencies ──
        if engineering_evidence.dependency_graph:
            validation_errors = self.data_collector.validate_dependencies(
                engineering_evidence.dependency_graph,
                [node.name for node in engineering_evidence.ast_nodes]
            )
            if validation_errors:
                logger.warning(f"Dependency validation errors: {validation_errors}")
                engineering_evidence.limitations.extend(validation_errors)
        
        # Add limitation if target was not directly resolved
        if not target_resolved:
            engineering_evidence.limitations.append(
                f"Target '{target_name}' was not found as an exact node in the "
                f"repository graph. Evidence is based on text-based reference matching."
            )
        
        # Add limitation if filesystem was not available
        if not repo_on_disk:
            engineering_evidence.limitations.append(
                "Repository clone not available on disk. Reference Intelligence was "
                "skipped. Evidence is derived from database records only."
            )
        
        # ── Step 8: Calculate completeness and confidence ──
        engineering_evidence.calculate_data_completeness()
        engineering_evidence.generate_limitation_statements()
        
        # ── Step 9: Structured evidence summary log ──
        logger.info("-" * 40)
        logger.info("ENGINEERING EVIDENCE — COMPLETE")
        logger.info(f"  AST nodes:           {len(engineering_evidence.ast_nodes)}")
        logger.info(f"  Dependency edges:    {engineering_evidence.dependency_graph.total_edges if engineering_evidence.dependency_graph else 0}")
        logger.info(f"  Call graph entries:   {len(engineering_evidence.call_graph.function_calls) if engineering_evidence.call_graph else 0}")
        logger.info(f"  Classes:             {len(engineering_evidence.classes)}")
        logger.info(f"  Functions:           {len(engineering_evidence.functions)}")
        logger.info(f"  API routes:          {len(engineering_evidence.api_routes)}")
        logger.info(f"  Imports:             {len(engineering_evidence.imports)}")
        logger.info(f"  Total references:    {engineering_evidence.total_references}")
        logger.info(f"  Data completeness:   {engineering_evidence.data_completeness}")
        logger.info(f"  Evidence confidence: {engineering_evidence.evidence_confidence:.2f}")
        logger.info(f"  Limitations:         {len(engineering_evidence.limitations)}")
        logger.info("-" * 40)
        
        return engineering_evidence
    
    # ──────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────
    
    async def _validate_repository(self, repo_id: UUID, db: AsyncSession) -> bool:
        """Check that the repository exists and has been analyzed."""
        try:
            result = await db.execute(
                select(Repo.id, Repo.full_name, Repo.analysis_status)
                .where(Repo.id == repo_id)
            )
            row = result.one_or_none()
            if not row:
                logger.error(f"Repo {repo_id} does not exist in database")
                return False
            
            repo_id_val, full_name, status = row
            logger.info(f"Repository validated: {full_name} (status={status})")
            
            if status not in ("completed", "completed_with_warnings"):
                logger.warning(
                    f"Repository {full_name} analysis status is '{status}' — "
                    f"evidence may be incomplete or unavailable."
                )
            
            # Check node count
            count_result = await db.execute(
                select(sa_func.count(Node.id)).where(Node.repo_id == repo_id)
            )
            node_count = count_result.scalar() or 0
            logger.info(f"Repository has {node_count} nodes in database")
            
            if node_count == 0:
                logger.warning(
                    f"Repository {full_name} has 0 nodes — AST data not available. "
                    f"Has the repository been fully analyzed?"
                )
            
            return True
        except Exception as e:
            logger.error(f"Error validating repository: {e}")
            return False

    async def _resolve_target_id(
        self,
        repo_id: UUID,
        target_name: str,
        db: AsyncSession
    ) -> Optional[UUID]:
        """Resolve target_id from target_name using database."""
        try:
            result = await db.execute(
                select(Node.id)
                .where(
                    Node.repo_id == repo_id,
                    Node.name.ilike(f"%{target_name}%")
                )
                .limit(1)
            )
            node = result.scalar_one_or_none()
            return node if node else None
        except Exception as e:
            logger.error(f"Error resolving target_id: {e}")
            return None
    
    async def _resolve_repo_path(
        self,
        repo_id: UUID,
        db: AsyncSession
    ) -> Optional[str]:
        """
        Resolve a repository path from repo_id.
        
        The Repo model does NOT have a `clone_path` column — repositories are
        cloned temporarily during analysis and then deleted. Instead, we use
        `Repo.full_name` (e.g. "owner/repo-name") to construct a virtual
        identifier. If the repository happens to still be on disk (e.g. during
        re-analysis), we return the real path.
        """
        try:
            result = await db.execute(
                select(Repo.full_name)
                .where(Repo.id == repo_id)
            )
            full_name = result.scalar_one_or_none()
            if not full_name:
                logger.warning(f"Repo {repo_id} not found when resolving path")
                return None
            
            # Check common clone locations (tempdir pattern used by repo_fetcher)
            import tempfile, os
            possible_paths = [
                Path(tempfile.gettempdir()) / "devbrain_clones" / full_name.replace("/", "_"),
                Path(tempfile.gettempdir()) / full_name.replace("/", "_"),
            ]
            
            for candidate in possible_paths:
                if candidate.is_dir():
                    logger.info(f"Found repo clone on disk: {candidate}")
                    return str(candidate)
            
            # No clone on disk — return full_name as a virtual identifier
            # (the pipeline will operate in DB-only mode)
            logger.info(
                f"No local clone found for '{full_name}'. "
                f"Pipeline will operate in database-only mode."
            )
            return full_name
            
        except Exception as e:
            logger.error(f"Error resolving repo_path: {e}")
            return None
    
    async def _collect_edges_from_db(
        self,
        repo_id: UUID,
        target_name: str,
        db: AsyncSession
    ) -> list[Dict[str, Any]]:
        """Collect edges from the Edge table for the target entity."""
        try:
            # Find nodes matching the target name
            target_nodes = await db.execute(
                select(Node.id, Node.name, Node.full_path)
                .where(
                    Node.repo_id == repo_id,
                    Node.name.ilike(f"%{target_name}%")
                )
            )
            target_rows = target_nodes.all()
            if not target_rows:
                return []
            
            target_ids = [row[0] for row in target_rows]
            
            # Get all edges involving these nodes (both directions)
            from sqlalchemy import or_
            edge_result = await db.execute(
                select(Edge)
                .where(
                    Edge.repo_id == repo_id,
                    or_(
                        Edge.from_node_id.in_(target_ids),
                        Edge.to_node_id.in_(target_ids)
                    )
                )
            )
            edges = edge_result.scalars().all()
            
            # Resolve node names for edges
            all_node_ids = set()
            for edge in edges:
                all_node_ids.add(edge.from_node_id)
                all_node_ids.add(edge.to_node_id)
            
            if not all_node_ids:
                return []
            
            node_result = await db.execute(
                select(Node.id, Node.name, Node.full_path)
                .where(Node.id.in_(all_node_ids))
            )
            node_map = {row[0]: (row[1], row[2]) for row in node_result.all()}
            
            edge_data = []
            for edge in edges:
                from_info = node_map.get(edge.from_node_id, ("unknown", None))
                to_info = node_map.get(edge.to_node_id, ("unknown", None))
                edge_data.append({
                    'from_name': from_info[0],
                    'to_name': to_info[0],
                    'edge_type': edge.edge_type,
                    'weight': edge.weight,
                    'file_path': from_info[1]
                })
            
            logger.info(f"Collected {len(edge_data)} edges from DB for '{target_name}'")
            return edge_data
            
        except Exception as e:
            logger.error(f"Error collecting edges from DB: {e}")
            return []
    
    def _build_evidence_from_db_data(
        self,
        repo_id: UUID,
        target_id: UUID,
        target_name: str,
        target_type: str,
        repository_data: Dict[str, Any],
    ) -> EngineeringEvidence:
        """
        Build engineering evidence directly from database data
        when Reference Intelligence is not available (no filesystem).
        """
        from .models import (
            EvidenceGroup, EvidenceCategory, FailureMode,
            RiskCategory, RiskAssessment
        )
        
        # Count data to determine confidence
        ast_count = len(repository_data.get('ast_nodes', []))
        dep_edges = repository_data.get('dependency_graph')
        dep_count = dep_edges.total_edges if dep_edges else 0
        class_count = len(repository_data.get('classes', []))
        func_count = len(repository_data.get('functions', []))
        import_count = len(repository_data.get('imports', []))
        route_count = len(repository_data.get('api_routes', []))
        
        total_data_points = ast_count + dep_count + class_count + func_count + import_count + route_count
        
        # Calculate confidence from available data
        if total_data_points > 50:
            confidence = 0.7
        elif total_data_points > 20:
            confidence = 0.5
        elif total_data_points > 5:
            confidence = 0.3
        else:
            confidence = 0.1
        
        # Determine criticality from dependency count
        if dep_count > 20:
            criticality = Criticality.HIGH
        elif dep_count > 5:
            criticality = Criticality.MEDIUM
        else:
            criticality = Criticality.LOW
        
        impact_score = min(dep_count / 30.0, 1.0)
        
        summary_parts = [
            f"Analysis of '{target_name}' based on {ast_count} AST nodes, "
            f"{dep_count} dependency edges, {class_count} classes, "
            f"{func_count} functions, and {import_count} imports."
        ]
        if dep_count > 0:
            summary_parts.append(
                f"The entity has {dep_count} dependency connections in the repository graph."
            )
        else:
            summary_parts.append(
                "No direct dependency connections found in the repository graph."
            )
        
        evidence = EngineeringEvidence(
            target_id=target_id,
            target_name=target_name,
            target_type=target_type,
            repo_id=repo_id,
            overall_summary=" ".join(summary_parts),
            overall_criticality=criticality,
            overall_impact_score=impact_score,
            overall_confidence=confidence,
            evidence_confidence=confidence,
            total_references=dep_count,
        )
        
        return evidence
    
    def _error_evidence(
        self,
        repo_id: UUID,
        target_name: str,
        target_type: str,
        reason: str,
    ) -> EngineeringEvidence:
        """Return structured error evidence when the pipeline cannot proceed."""
        logger.error(f"Engineering Evidence ERROR: {reason}")
        return EngineeringEvidence(
            target_id=repo_id,
            target_name=target_name,
            target_type=target_type,
            repo_id=repo_id,
            overall_summary=f"Engineering evidence generation failed: {reason}",
            overall_criticality=Criticality.LOW,
            overall_impact_score=0.0,
            overall_confidence=0.0,
            evidence_confidence=0.0,
            limitations=[reason],
        )
