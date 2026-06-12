"""
Workflow Discovery Engine — deterministic clustering from graph + structure.
No LLM. Minimum 3 nodes per workflow.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.node import Node
from app.models.workflow import (
    Workflow,
    WorkflowApi,
    WorkflowFile,
    WorkflowNode,
    WorkflowService,
)
from app.services.service_mapper import infer_workflow_type, map_workflow_to_service

logger = logging.getLogger(__name__)

MIN_WORKFLOW_NODES = 3


@dataclass
class WorkflowSeed:
    name: str
    description: str
    criticality: str
    workflow_type: str
    node_patterns: re.Pattern[str]
    path_patterns: re.Pattern[str]
    api_patterns: re.Pattern[str] = field(default_factory=lambda: re.compile(r"$^"))


WORKFLOW_SEEDS: tuple[WorkflowSeed, ...] = (
    WorkflowSeed(
        name="GitHub Authentication",
        description="OAuth sign-in, GitHub callback, and token exchange.",
        criticality="high",
        workflow_type="authentication",
        node_patterns=re.compile(
            r"github|oauth|auth|login|callback|sign.?in|save_github|token",
            re.I,
        ),
        path_patterns=re.compile(r"auth|oauth|github|login", re.I),
        api_patterns=re.compile(r"/auth|/oauth|/github|callback", re.I),
    ),
    WorkflowSeed(
        name="Session Management",
        description="Session creation, validation, and user context.",
        criticality="high",
        workflow_type="session",
        node_patterns=re.compile(r"session|cookie|get_current_user|jwt", re.I),
        path_patterns=re.compile(r"session|auth|middleware", re.I),
        api_patterns=re.compile(r"/session|/me|current.?user", re.I),
    ),
    WorkflowSeed(
        name="Repository Connection",
        description="Connect and sync GitHub repositories.",
        criticality="high",
        workflow_type="integration",
        node_patterns=re.compile(r"connect|repo|repository|fetch_github|sync", re.I),
        path_patterns=re.compile(r"repo|connect|github", re.I),
        api_patterns=re.compile(r"/repos|connect", re.I),
    ),
    WorkflowSeed(
        name="Repository Analysis",
        description="Parse repository, build nodes and edges.",
        criticality="medium",
        workflow_type="analysis",
        node_patterns=re.compile(r"analyz|parser|parse|scan|index|ingest", re.I),
        path_patterns=re.compile(r"analy|parser|services/analysis", re.I),
        api_patterns=re.compile(r"/analyze|/analysis", re.I),
    ),
    WorkflowSeed(
        name="Impact Radar",
        description="Change impact and dependency intelligence.",
        criticality="medium",
        workflow_type="intelligence",
        node_patterns=re.compile(r"impact|resolver|blast|risk|workflow", re.I),
        path_patterns=re.compile(r"impact|resolver", re.I),
        api_patterns=re.compile(r"/impact", re.I),
    ),
    WorkflowSeed(
        name="Dashboard Experience",
        description="Dashboard UI and repo overview APIs.",
        criticality="medium",
        workflow_type="frontend",
        node_patterns=re.compile(r"dashboard|frontend|page|component", re.I),
        path_patterns=re.compile(r"frontend|dashboard|pages", re.I),
        api_patterns=re.compile(r"/dashboard", re.I),
    ),
    WorkflowSeed(
        name="Public API Surface",
        description="Public HTTP routes exposed by the API layer.",
        criticality="medium",
        workflow_type="api",
        node_patterns=re.compile(r"api_route|router|endpoint", re.I),
        path_patterns=re.compile(r"routers|api/", re.I),
        api_patterns=re.compile(r"^/api", re.I),
    ),
)


@dataclass
class NodeRow:
    id: str
    name: str
    node_type: str
    file_path: str
    file_id: str | None
    http_method: str | None
    route_path: str | None
    full_path: str


class WorkflowDiscoveryService:
    async def discover_for_repo(self, repo_id: UUID, db: AsyncSession) -> int:
        """Replace repo workflows with freshly discovered clusters."""
        nodes = await self._load_nodes(repo_id, db)
        if len(nodes) < MIN_WORKFLOW_NODES:
            logger.info("Repo %s has too few nodes for workflow discovery", repo_id)
            return 0

        edges = await self._load_edges(repo_id, db)
        adjacency = self._build_adjacency(edges)

        await db.execute(delete(Workflow).where(Workflow.repo_id == repo_id))

        discovered: list[Workflow] = []
        assigned: set[str] = set()

        for seed in WORKFLOW_SEEDS:
            cluster_ids = self._match_seed(seed, nodes, assigned)
            cluster_ids = self._expand_cluster(cluster_ids, nodes, adjacency, seed, assigned)
            if len(cluster_ids) < MIN_WORKFLOW_NODES:
                continue
            wf = await self._persist_workflow(
                repo_id, seed, cluster_ids, nodes, edges, db
            )
            discovered.append(wf)
            assigned.update(cluster_ids)

        extra = self._discover_folder_clusters(nodes, assigned, adjacency)
        for name, cluster_ids, evidence in extra:
            if len(cluster_ids) < MIN_WORKFLOW_NODES:
                continue
            seed = WorkflowSeed(
                name=name,
                description=f"Clustered from shared folder and call graph ({evidence}).",
                criticality="low",
                workflow_type="cluster",
                node_patterns=re.compile(re.escape(name[:20]), re.I),
                path_patterns=re.compile(r".", re.I),
            )
            wf = await self._persist_workflow(
                repo_id, seed, cluster_ids, nodes, edges, db, folder_evidence=evidence
            )
            discovered.append(wf)
            assigned.update(cluster_ids)

        await db.flush()
        logger.info("Discovered %d workflows for repo %s", len(discovered), repo_id)
        return len(discovered)

    async def _load_nodes(self, repo_id: UUID, db: AsyncSession) -> dict[str, NodeRow]:
        rows = (
            await db.execute(
                text("""
                    SELECT n.id, n.name, n.node_type, n.full_path, n.file_id,
                           n.http_method, n.route_path,
                           COALESCE(rf.file_path, n.full_path) AS file_path
                    FROM nodes n
                    LEFT JOIN repo_files rf ON n.file_id = rf.id
                    WHERE n.repo_id = :repo_id
                """),
                {"repo_id": str(repo_id)},
            )
        ).mappings()
        return {
            str(r["id"]): NodeRow(
                id=str(r["id"]),
                name=r["name"] or "",
                node_type=r["node_type"] or "function",
                file_path=r["file_path"] or "",
                file_id=str(r["file_id"]) if r["file_id"] else None,
                http_method=r["http_method"],
                route_path=r["route_path"],
                full_path=r["full_path"] or "",
            )
            for r in rows
        }

    async def _load_edges(
        self, repo_id: UUID, db: AsyncSession
    ) -> list[tuple[str, str]]:
        rows = (
            await db.execute(
                text("""
                    SELECT from_node_id, to_node_id FROM edges
                    WHERE repo_id = :repo_id
                """),
                {"repo_id": str(repo_id)},
            )
        ).mappings()
        return [(str(r["from_node_id"]), str(r["to_node_id"])) for r in rows]

    def _build_adjacency(
        self, edges: list[tuple[str, str]]
    ) -> dict[str, set[str]]:
        adj: dict[str, set[str]] = defaultdict(set)
        for a, b in edges:
            adj[a].add(b)
            adj[b].add(a)
        return adj

    def _match_seed(
        self,
        seed: WorkflowSeed,
        nodes: dict[str, NodeRow],
        assigned: set[str],
    ) -> set[str]:
        matched: set[str] = set()
        for nid, node in nodes.items():
            if nid in assigned:
                continue
            blob = f"{node.name} {node.file_path} {node.full_path} {node.route_path or ''}"
            if seed.node_patterns.search(blob) or seed.path_patterns.search(node.file_path):
                matched.add(nid)
            if node.node_type == "api_route" and seed.api_patterns.search(
                f"{node.http_method or 'GET'} {node.route_path or ''}"
            ):
                matched.add(nid)
        return matched

    def _expand_cluster(
        self,
        cluster: set[str],
        nodes: dict[str, NodeRow],
        adjacency: dict[str, set[str]],
        seed: WorkflowSeed,
        assigned: set[str],
    ) -> set[str]:
        expanded = set(cluster)
        frontier = list(cluster)
        for _ in range(3):
            next_frontier: list[str] = []
            for nid in frontier:
                for neighbor in adjacency.get(nid, ()):
                    if neighbor in assigned or neighbor in expanded:
                        continue
                    node = nodes.get(neighbor)
                    if not node:
                        continue
                    blob = f"{node.name} {node.file_path}"
                    if seed.node_patterns.search(blob) or seed.path_patterns.search(
                        node.file_path
                    ):
                        expanded.add(neighbor)
                        next_frontier.append(neighbor)
            frontier = next_frontier
            if not frontier:
                break
        return expanded

    def _discover_folder_clusters(
        self,
        nodes: dict[str, NodeRow],
        assigned: set[str],
        adjacency: dict[str, set[str]],
    ) -> list[tuple[str, set[str], str]]:
        """Group unassigned nodes by top-level backend/frontend folder."""
        folder_groups: dict[str, set[str]] = defaultdict(set)
        for nid, node in nodes.items():
            if nid in assigned:
                continue
            parts = (node.file_path or "").replace("\\", "/").split("/")
            if len(parts) >= 2:
                key = "/".join(parts[:2])
            elif parts:
                key = parts[0]
            else:
                key = "misc"
            folder_groups[key].add(nid)

        results: list[tuple[str, set[str], str]] = []
        for folder, nids in folder_groups.items():
            if len(nids) < MIN_WORKFLOW_NODES:
                continue
            connected = self._connected_subset(nids, adjacency)
            if len(connected) >= MIN_WORKFLOW_NODES:
                label = folder.replace("/", " ").title() + " Cluster"
                results.append((label, connected, f"folder:{folder}"))
        return results[:3]

    def _connected_subset(
        self, nids: set[str], adjacency: dict[str, set[str]]
    ) -> set[str]:
        if not nids:
            return set()
        start = next(iter(nids))
        seen = {start}
        stack = [start]
        while stack:
            cur = stack.pop()
            for nb in adjacency.get(cur, ()):
                if nb in nids and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        return seen if len(seen) >= MIN_WORKFLOW_NODES else nids

    def _score_confidence(
        self,
        cluster_ids: set[str],
        nodes: dict[str, NodeRow],
        edges: list[tuple[str, str]],
        seed: WorkflowSeed,
    ) -> tuple[float, str, dict]:
        cluster = cluster_ids
        internal_edges = sum(
            1 for a, b in edges if a in cluster and b in cluster
        )
        max_edges = max(1, len(cluster) * (len(cluster) - 1) // 2)
        connectivity = min(1.0, internal_edges / max(1, len(cluster)))
        density = min(1.0, len(cluster) / 20.0)

        api_count = sum(
            1
            for nid in cluster
            if nodes[nid].node_type == "api_route"
            or nodes[nid].route_path
        )
        api_score = min(1.0, api_count / 3.0)

        folders = {nodes[nid].file_path.rsplit("/", 1)[0] for nid in cluster if nodes[nid].file_path}
        folder_score = 1.0 if len(folders) <= 3 else max(0.4, 3.0 / len(folders))

        name_hits = sum(
            1
            for nid in cluster
            if seed.node_patterns.search(nodes[nid].name)
        )
        naming_score = min(1.0, name_hits / max(1, len(cluster) * 0.5))

        raw = (
            0.30 * density
            + 0.30 * connectivity
            + 0.20 * api_score
            + 0.10 * folder_score
            + 0.10 * naming_score
        )
        confidence = round(min(0.98, max(0.55, raw * 0.95 + 0.05)), 4)
        reasoning = (
            f"{len(cluster)} nodes, {internal_edges} internal edges, "
            f"{api_count} API associations, {len(folders)} folder groups."
        )
        evidence = {
            "node_count": len(cluster),
            "internal_edges": internal_edges,
            "api_count": api_count,
            "folder_groups": len(folders),
            "density_score": round(density, 3),
            "connectivity_score": round(connectivity, 3),
            "api_score": round(api_score, 3),
            "folder_score": round(folder_score, 3),
            "naming_score": round(naming_score, 3),
        }
        return confidence, reasoning, evidence

    async def _persist_workflow(
        self,
        repo_id: UUID,
        seed: WorkflowSeed,
        cluster_ids: set[str],
        nodes: dict[str, NodeRow],
        edges: list[tuple[str, str]],
        db: AsyncSession,
        *,
        folder_evidence: str | None = None,
    ) -> Workflow:
        confidence, reasoning, evidence = self._score_confidence(
            cluster_ids, nodes, edges, seed
        )
        if folder_evidence:
            evidence["folder_cluster"] = folder_evidence

        wf = Workflow(
            repo_id=repo_id,
            name=seed.name,
            description=seed.description,
            criticality=seed.criticality,
            workflow_type=seed.workflow_type or infer_workflow_type(seed.name),
            confidence=confidence,
            reasoning=reasoning,
            source_evidence=evidence,
        )
        db.add(wf)
        await db.flush()

        file_ids: set[str] = set()
        for nid in cluster_ids:
            node = nodes[nid]
            db.add(
                WorkflowNode(
                    workflow_id=wf.id,
                    node_id=UUID(nid),
                    relationship_type="member",
                )
            )
            if node.file_id:
                file_ids.add(node.file_id)

        for fid in file_ids:
            db.add(WorkflowFile(workflow_id=wf.id, file_id=UUID(fid)))

        api_routes: set[str] = set()
        for nid in cluster_ids:
            node = nodes[nid]
            if node.route_path:
                route = f"{node.http_method or 'GET'} {node.route_path}"
                api_routes.add(route)
        for route in sorted(api_routes)[:25]:
            db.add(WorkflowApi(workflow_id=wf.id, api_route=route))

        service_name = map_workflow_to_service(seed.name)
        db.add(WorkflowService(workflow_id=wf.id, service_name=service_name))

        return wf

    async def list_workflows(self, repo_id: UUID, db: AsyncSession) -> list[Workflow]:
        result = await db.execute(
            select(Workflow)
            .where(Workflow.repo_id == repo_id)
            .options(
                selectinload(Workflow.nodes),
                selectinload(Workflow.apis),
                selectinload(Workflow.services),
            )
            .order_by(Workflow.confidence.desc())
        )
        return list(result.scalars().all())

    async def get_workflow(
        self, repo_id: UUID, workflow_id: UUID, db: AsyncSession
    ) -> Workflow | None:
        result = await db.execute(
            select(Workflow)
            .where(Workflow.repo_id == repo_id, Workflow.id == workflow_id)
            .options(
                selectinload(Workflow.nodes),
                selectinload(Workflow.apis),
                selectinload(Workflow.services),
                selectinload(Workflow.files),
            )
        )
        return result.scalar_one_or_none()
