"""Flow Reconstruction Engine.

Transforms the EXISTING repository graph (nodes / edges) into meaningful
architectural flows by deterministic graph traversal (BFS / DFS). Every step in
every flow is backed by a real edge in the `edges` table, so the output is
reproducible and contains no AI / LLM / hallucinated content.

Five flow types are reconstructed:

  1. api_request        Client → API Route → Service → Database (forward BFS)
  2. authentication     API Route → Auth dependency → guarded resource (forward BFS)
  3. repo_analysis      Analysis entrypoint → parser/graph services → tables (forward BFS)
  4. db_interaction     Table ← writers / readers ← their callers (reverse BFS)
  5. service_dependency Service → service / call / DI chain (forward DFS)

A flow is identified by a DETERMINISTIC id `{flow_type}::{root_node_id}`. Nothing
is persisted: GET /flows/{flow_id} simply re-runs the single traversal for that
root, so list and detail can never disagree.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Edge, Node, RepoFile
from app.schemas.flow import (
    Flow,
    FlowNodeRef,
    FlowStep,
    FlowSummary,
)

logger = logging.getLogger(__name__)

# ── Edge vocabulary (matches code_parser.py / analysis_collect.py) ────────
CALL_EDGES = frozenset({"calls", "api_calls"})
SERVICE_EDGES = frozenset({"uses_service"})
TABLE_READ_EDGES = frozenset({"reads_table"})
TABLE_WRITE_EDGES = frozenset({"writes_table", "updates_table", "deletes_table"})
TABLE_EDGES = TABLE_READ_EDGES | TABLE_WRITE_EDGES
DEP_EDGES = frozenset({"imports", "dependency_injection", "inherits"})
AUTH_EDGES = frozenset({"auth_dependency", "middleware_dependency"})
EXTERNAL_EDGES = frozenset({"external_api"})

# Resource node types that anchor "dependencies" and "critical" classification.
RESOURCE_TYPES = frozenset({"service", "database_table", "external_api"})
CRITICAL_TYPES = frozenset({"api_route", "service", "database_table", "external_api"})

# Heuristic seeding ONLY for picking analysis-flow roots. The flow *content* is
# still pure graph evidence; these keywords just choose which entrypoints to
# treat as analysis pipelines.
ANALYSIS_KEYWORDS = (
    "analyz",
    "analysis",
    "parse",
    "parser",
    "ingest",
    "scan",
    "index",
    "extract",
    "reconstruct",
    "discover",
    "graph",
)

# ── Bounds: keep traversals cheap and payloads predictable ────────────────
MAX_DEPTH = 6
MAX_NODES_PER_FLOW = 60
MAX_EDGES_PER_FLOW = 120
MAX_ROOTS_PER_TYPE = 25  # roots materialised into the list endpoint
MAX_GRAPH_EDGES = 40000  # safety cap on what we load into memory


@dataclass
class GraphIndex:
    """In-memory view of one repo's graph, loaded once per request."""

    meta: dict[str, dict] = field(default_factory=dict)
    # adjacency: node_id -> list of (neighbor_id, edge_type)
    fwd: dict[str, list[tuple[str, str]]] = field(default_factory=lambda: defaultdict(list))
    rev: dict[str, list[tuple[str, str]]] = field(default_factory=lambda: defaultdict(list))
    # real directed edges keyed for subgraph extraction: (from,to) -> set(edge_type)
    edge_types: dict[tuple[str, str], set[str]] = field(default_factory=lambda: defaultdict(set))
    by_type: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def node_ref(self, node_id: str) -> FlowNodeRef:
        m = self.meta.get(node_id, {})
        return FlowNodeRef(
            id=node_id,
            name=m.get("name", node_id[:8]),
            node_type=m.get("node_type", "unknown"),
            file_path=m.get("file_path"),
            http_method=m.get("http_method"),
            route_path=m.get("route_path"),
        )


# ── Flow-type traversal configuration ─────────────────────────────────────
# direction: "fwd" follows edges as written; "rev" walks against them.
# algo: "bfs" (layered request flows) or "dfs" (dependency chains).
@dataclass(frozen=True)
class FlowSpec:
    flow_type: str
    label: str
    allowed: frozenset[str]
    direction: str
    algo: str


FLOW_SPECS: dict[str, FlowSpec] = {
    "api_request": FlowSpec(
        "api_request",
        "API Request Flow",
        CALL_EDGES | SERVICE_EDGES | TABLE_EDGES | EXTERNAL_EDGES,
        "fwd",
        "bfs",
    ),
    "authentication": FlowSpec(
        "authentication",
        "Authentication Flow",
        AUTH_EDGES | CALL_EDGES | TABLE_EDGES,
        "fwd",
        "bfs",
    ),
    "repo_analysis": FlowSpec(
        "repo_analysis",
        "Repository Analysis Flow",
        CALL_EDGES | SERVICE_EDGES | TABLE_EDGES | EXTERNAL_EDGES,
        "fwd",
        "bfs",
    ),
    "db_interaction": FlowSpec(
        "db_interaction",
        "Database Interaction Flow",
        TABLE_EDGES | CALL_EDGES,
        "rev",
        "bfs",
    ),
    "service_dependency": FlowSpec(
        "service_dependency",
        "Service Dependency Flow",
        SERVICE_EDGES | CALL_EDGES | DEP_EDGES,
        "fwd",
        "dfs",
    ),
}


class FlowReconstructionService:
    # ── Graph loading ─────────────────────────────────────────────────────
    async def _load_index(self, repo_id: UUID, db: AsyncSession) -> GraphIndex:
        idx = GraphIndex()

        node_rows = (
            await db.execute(
                select(
                    Node.id,
                    Node.name,
                    Node.node_type,
                    Node.http_method,
                    Node.route_path,
                    RepoFile.file_path,
                )
                .outerjoin(RepoFile, Node.file_id == RepoFile.id)
                .where(Node.repo_id == repo_id)
            )
        ).all()
        for nid, name, ntype, method, route, fpath in node_rows:
            sid = str(nid)
            idx.meta[sid] = {
                "name": name,
                "node_type": ntype,
                "http_method": method,
                "route_path": route,
                "file_path": fpath,
            }
            idx.by_type[ntype].append(sid)

        edge_rows = (
            await db.execute(
                select(Edge.from_node_id, Edge.to_node_id, Edge.edge_type)
                .where(Edge.repo_id == repo_id)
                .limit(MAX_GRAPH_EDGES)
            )
        ).all()
        for fid, tid, etype in edge_rows:
            f, t = str(fid), str(tid)
            if f == t or f not in idx.meta or t not in idx.meta:
                continue
            idx.fwd[f].append((t, etype))
            idx.rev[t].append((f, etype))
            idx.edge_types[(f, t)].add(etype)

        return idx

    # ── Generic bounded traversal ─────────────────────────────────────────
    def _collect_reachable(
        self, idx: GraphIndex, root_id: str, spec: FlowSpec
    ) -> tuple[dict[str, int], bool]:
        """Return {node_id: depth} reachable from root under the spec, plus a
        truncation flag. BFS yields layered depths; DFS yields chain order."""
        adj = idx.fwd if spec.direction == "fwd" else idx.rev
        depth = {root_id: 0}
        truncated = False

        def neighbors(nid: str) -> list[tuple[str, str]]:
            # Deterministic order: by neighbor name then id then edge_type.
            ns = [(nb, et) for nb, et in adj.get(nid, ()) if et in spec.allowed]
            ns.sort(key=lambda x: (idx.meta.get(x[0], {}).get("name", x[0]), x[0], x[1]))
            return ns

        if spec.algo == "bfs":
            frontier: deque[str] = deque([root_id])
            while frontier:
                cur = frontier.popleft()
                d = depth[cur]
                if d >= MAX_DEPTH:
                    continue
                for nb, _et in neighbors(cur):
                    if nb in depth:
                        continue
                    if len(depth) >= MAX_NODES_PER_FLOW:
                        truncated = True
                        break
                    depth[nb] = d + 1
                    frontier.append(nb)
                else:
                    continue
                break
        else:  # dfs
            stack: list[tuple[str, int]] = [(root_id, 0)]
            while stack:
                cur, d = stack.pop()
                if d >= MAX_DEPTH:
                    continue
                # reversed() so sorted neighbors are visited in order under LIFO
                for nb, _et in reversed(neighbors(cur)):
                    if nb in depth:
                        continue
                    if len(depth) >= MAX_NODES_PER_FLOW:
                        truncated = True
                        break
                    depth[nb] = d + 1
                    stack.append((nb, d + 1))

        return depth, truncated

    def _build_flow(self, idx: GraphIndex, root_id: str, spec: FlowSpec) -> Flow | None:
        depth, truncated = self._collect_reachable(idx, root_id, spec)
        if len(depth) <= 1:
            return None  # isolated root → no flow to reconstruct

        included = set(depth)

        # Real edges fully inside the reachable set (true subgraph, real
        # directions) → these are the flow steps. Gives honest in/out degree.
        raw_steps: list[tuple[str, str, str]] = []
        for (f, t), etypes in idx.edge_types.items():
            if f not in included or t not in included:
                continue
            for et in etypes:
                if et in spec.allowed:
                    raw_steps.append((f, t, et))

        # Deterministic ordering: by progression depth, then names.
        def step_key(s: tuple[str, str, str]) -> tuple:
            f, t, et = s
            df, dt = depth.get(f, 0), depth.get(t, 0)
            return (
                min(df, dt),
                max(df, dt),
                idx.meta.get(f, {}).get("name", f),
                idx.meta.get(t, {}).get("name", t),
                et,
            )

        raw_steps.sort(key=step_key)
        if len(raw_steps) > MAX_EDGES_PER_FLOW:
            raw_steps = raw_steps[:MAX_EDGES_PER_FLOW]
            truncated = True

        steps = [
            FlowStep(
                order=i,
                depth=max(depth.get(f, 0), depth.get(t, 0)),
                edge_type=et,
                from_node=idx.node_ref(f),
                to_node=idx.node_ref(t),
            )
            for i, (f, t, et) in enumerate(raw_steps)
        ]

        # In-degree within the flow subgraph → hub detection.
        indeg: dict[str, int] = defaultdict(int)
        outdeg: dict[str, int] = defaultdict(int)
        for f, t, _et in raw_steps:
            indeg[t] += 1
            outdeg[f] += 1

        critical_ids: list[str] = []
        seen_crit: set[str] = set()

        def add_crit(nid: str) -> None:
            if nid not in seen_crit:
                seen_crit.add(nid)
                critical_ids.append(nid)

        add_crit(root_id)
        for nid in included:
            ntype = idx.meta.get(nid, {}).get("node_type")
            if ntype in CRITICAL_TYPES or indeg[nid] >= 2 or outdeg[nid] >= 3:
                add_crit(nid)
        critical_ids.sort(key=lambda n: (idx.meta.get(n, {}).get("name", n), n))

        dependency_ids = sorted(
            (
                nid
                for nid in included
                if nid != root_id and idx.meta.get(nid, {}).get("node_type") in RESOURCE_TYPES
            ),
            key=lambda n: (idx.meta.get(n, {}).get("name", n), n),
        )

        root_ref = idx.node_ref(root_id)
        return Flow(
            flow_id=f"{spec.flow_type}::{root_id}",
            flow_name=self._flow_name(spec, root_ref),
            flow_type=spec.flow_type,
            root_node=root_ref,
            steps=steps,
            critical_nodes=[idx.node_ref(n) for n in critical_ids],
            dependencies=[idx.node_ref(n) for n in dependency_ids],
            node_count=len(included),
            edge_count=len(steps),
            truncated=truncated,
        )

    @staticmethod
    def _flow_name(spec: FlowSpec, root: FlowNodeRef) -> str:
        if spec.flow_type == "api_request" and root.http_method and root.route_path:
            return f"{spec.label}: {root.http_method} {root.route_path}"
        return f"{spec.label}: {root.name}"

    # ── Root selection per flow type ──────────────────────────────────────
    def _roots_for_type(self, idx: GraphIndex, flow_type: str) -> list[str]:
        if flow_type == "api_request":
            roots = list(idx.by_type.get("api_route", []))
        elif flow_type == "authentication":
            # Any node that issues an auth/middleware dependency edge.
            roots = [
                f
                for (f, _t), ets in idx.edge_types.items()
                if ets & AUTH_EDGES
            ]
        elif flow_type == "repo_analysis":
            roots = [
                nid
                for nid, m in idx.meta.items()
                if m.get("node_type") in ("api_route", "service", "function", "method")
                and self._matches_analysis(m)
            ]
        elif flow_type == "db_interaction":
            roots = list(idx.by_type.get("database_table", []))
        elif flow_type == "service_dependency":
            roots = list(idx.by_type.get("service", []))
        else:
            roots = []
        # Stable order; de-dup.
        uniq = sorted(set(roots), key=lambda n: (idx.meta.get(n, {}).get("name", n), n))
        return uniq

    @staticmethod
    def _matches_analysis(meta: dict) -> bool:
        hay = f"{meta.get('name', '')} {meta.get('route_path', '') or ''}".lower()
        return any(k in hay for k in ANALYSIS_KEYWORDS)

    # ── Public API ────────────────────────────────────────────────────────
    async def list_flows(self, repo_id: UUID, db: AsyncSession) -> tuple[
        list[FlowSummary], dict[str, int]
    ]:
        idx = await self._load_index(repo_id, db)
        summaries: list[FlowSummary] = []
        type_counts: dict[str, int] = {}

        for flow_type, spec in FLOW_SPECS.items():
            roots = self._roots_for_type(idx, flow_type)
            built = 0
            for root_id in roots:
                if built >= MAX_ROOTS_PER_TYPE:
                    break
                flow = self._build_flow(idx, root_id, spec)
                if flow is None:
                    continue
                built += 1
                summaries.append(
                    FlowSummary(
                        flow_id=flow.flow_id,
                        flow_name=flow.flow_name,
                        flow_type=flow.flow_type,
                        root_node=flow.root_node,
                        step_count=flow.edge_count,
                        critical_node_count=len(flow.critical_nodes),
                    )
                )
            if built:
                type_counts[flow_type] = built

        return summaries, type_counts

    async def get_flow(self, repo_id: UUID, flow_id: str, db: AsyncSession) -> Flow | None:
        spec, root_id = self._parse_flow_id(flow_id)
        if spec is None or root_id is None:
            return None
        idx = await self._load_index(repo_id, db)
        if root_id not in idx.meta:
            return None
        return self._build_flow(idx, root_id, spec)

    async def flows_from_node(
        self, repo_id: UUID, node_id: str, db: AsyncSession
    ) -> tuple[FlowNodeRef | None, list[Flow]]:
        idx = await self._load_index(repo_id, db)
        if node_id not in idx.meta:
            return None, []
        node_ref = idx.node_ref(node_id)

        flows: list[Flow] = []
        seen: set[str] = set()
        for spec in self._candidate_specs(idx, node_id):
            flow = self._build_flow(idx, node_id, spec)
            if flow and flow.flow_id not in seen:
                seen.add(flow.flow_id)
                flows.append(flow)
        return node_ref, flows

    def _candidate_specs(self, idx: GraphIndex, node_id: str) -> list[FlowSpec]:
        """Which flow types can this node root? Based on its type + incident edges."""
        ntype = idx.meta.get(node_id, {}).get("node_type")
        out_types: set[str] = {et for (f, _t), ets in idx.edge_types.items() if f == node_id for et in ets}
        in_types: set[str] = {et for (_f, t), ets in idx.edge_types.items() if t == node_id for et in ets}

        specs: list[FlowSpec] = []
        if ntype == "api_route":
            specs.append(FLOW_SPECS["api_request"])
            if out_types & AUTH_EDGES:
                specs.append(FLOW_SPECS["authentication"])
        if ntype == "service":
            specs.append(FLOW_SPECS["service_dependency"])
            specs.append(FLOW_SPECS["api_request"])
        if ntype == "database_table" and in_types & TABLE_EDGES:
            specs.append(FLOW_SPECS["db_interaction"])
        if ntype in ("function", "method"):
            # Generic forward flow if it calls anything or touches resources.
            if out_types & (CALL_EDGES | SERVICE_EDGES | TABLE_EDGES | EXTERNAL_EDGES):
                specs.append(FLOW_SPECS["api_request"])
            if out_types & AUTH_EDGES:
                specs.append(FLOW_SPECS["authentication"])
        if self._matches_analysis(idx.meta.get(node_id, {})) and ntype in (
            "api_route",
            "service",
            "function",
            "method",
        ):
            specs.append(FLOW_SPECS["repo_analysis"])
        return specs

    @staticmethod
    def _parse_flow_id(flow_id: str) -> tuple[FlowSpec | None, str | None]:
        if "::" not in flow_id:
            return None, None
        flow_type, _, root_id = flow_id.partition("::")
        spec = FLOW_SPECS.get(flow_type)
        if spec is None or not root_id:
            return None, None
        return spec, root_id
