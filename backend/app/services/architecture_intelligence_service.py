"""Architecture Intelligence V2 — deterministic, graph-first analysis engine.

Every score, finding, and recommendation is computed in pure Python from graph
facts stored in the database (nodes + edges + impact_metrics). The LLM is NEVER
involved. Results are reproducible and free of hallucinated architecture.

This engine powers:
  • Critical Component Detector   — influence scoring
  • Bottleneck Detector           — God services, oversized modules, fan explosions
  • Refactor Opportunity Engine   — cycles, coupling, violations
  • Change Risk Predictor         — blast radius for a given node
  • Architecture Findings         — deterministic top-10 engineering findings
  • Intelligence Dashboard        — aggregated scores + sections
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Edge, Node, RepoFile
from app.models.blast_radius import ImpactMetric
from app.schemas.intelligence import (
    ArchitectureViolation,
    Bottleneck,
    BottlenecksResponse,
    ChangeRiskReport,
    CouplingPair,
    CriticalComponent,
    CriticalComponentsResponse,
    CyclicDependency,
    Finding,
    FindingsResponse,
    ImpactedEntity,
    IntelligenceDashboard,
    RefactorOpportunitiesResponse,
)

logger = logging.getLogger(__name__)

# ── Thresholds (calibrated for typical repos, saturate at large ones) ────
GOD_SERVICE_FAN_OUT = 15
GOD_SERVICE_FAN_IN = 25
OVERSIZED_MODULE_NODES = 50  # children in the same file
FAN_IN_EXPLOSION = 20
FAN_OUT_EXPLOSION = 15
TIGHT_COUPLING_EDGE_THRESHOLD = 3  # edges between two nodes
MAX_CYCLE_LENGTH = 8
MAX_BFS_DEPTH = 6
MAX_RESULTS = 25
MAX_FINDINGS = 10

# Layer ordering for violation detection (lower → closer to user)
LAYER_ORDER = {
    "api_route": 0,
    "function": 1,
    "method": 1,
    "class": 1,
    "service": 2,
    "database_table": 3,
    "external_api": 4,
}


# ── In-memory graph index (loaded once per request) ─────────────────────

@dataclass
class _GraphIndex:
    """Lightweight in-memory view of a repo graph."""

    nodes: dict[str, dict] = field(default_factory=dict)
    fwd: dict[str, list[tuple[str, str, float]]] = field(
        default_factory=lambda: defaultdict(list),
    )
    rev: dict[str, list[tuple[str, str, float]]] = field(
        default_factory=lambda: defaultdict(list),
    )
    # (from, to) → set of edge_types
    edge_types: dict[tuple[str, str], set[str]] = field(
        default_factory=lambda: defaultdict(set),
    )
    # node_type → [node_ids]
    by_type: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list),
    )
    # file_path → [node_ids]
    by_file: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list),
    )
    # pre-computed metrics from impact_metrics table
    metrics: dict[str, dict] = field(default_factory=dict)

    @property
    def total_nodes(self) -> int:
        return len(self.nodes)

    @property
    def total_edges(self) -> int:
        return sum(len(v) for v in self.fwd.values())

    def in_degree(self, nid: str) -> int:
        return len(self.rev.get(nid, []))

    def out_degree(self, nid: str) -> int:
        return len(self.fwd.get(nid, []))


# ═══════════════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════════════


class ArchitectureIntelligenceService:
    """Deterministic architecture intelligence — graph in, scores out."""

    # ── Graph loading ──────────────────────────────────────────────────

    @staticmethod
    async def _load_index(repo_id: UUID, db: AsyncSession) -> _GraphIndex:
        idx = _GraphIndex()

        # Nodes
        node_rows = (
            await db.execute(
                select(
                    Node.id, Node.name, Node.node_type, Node.full_path,
                    Node.complexity_score, Node.is_exported, Node.is_async,
                    Node.http_method, Node.route_path,
                    RepoFile.file_path,
                )
                .outerjoin(RepoFile, Node.file_id == RepoFile.id)
                .where(Node.repo_id == repo_id)
            )
        ).all()

        for nid, name, ntype, full_path, cscore, exported, is_async, method, route, fpath in node_rows:
            sid = str(nid)
            idx.nodes[sid] = {
                "name": name,
                "node_type": ntype,
                "full_path": full_path,
                "file_path": fpath,
                "complexity_score": cscore or 0.0,
                "is_exported": exported,
                "is_async": is_async,
                "http_method": method,
                "route_path": route,
            }
            idx.by_type[ntype].append(sid)
            if fpath:
                idx.by_file[fpath].append(sid)

        # Edges
        edge_rows = (
            await db.execute(
                select(Edge.from_node_id, Edge.to_node_id, Edge.edge_type, Edge.weight)
                .where(Edge.repo_id == repo_id)
            )
        ).all()

        for fid, tid, etype, weight in edge_rows:
            f, t = str(fid), str(tid)
            if f == t or f not in idx.nodes or t not in idx.nodes:
                continue
            w = weight or 1.0
            idx.fwd[f].append((t, etype, w))
            idx.rev[t].append((f, etype, w))
            idx.edge_types[(f, t)].add(etype)

        # Pre-computed impact metrics (if available)
        metric_rows = (
            await db.execute(
                select(ImpactMetric).where(ImpactMetric.repo_id == repo_id)
            )
        ).scalars().all()

        for m in metric_rows:
            idx.metrics[str(m.node_id)] = {
                "centrality_score": m.centrality_score,
                "blast_radius_score": m.blast_radius_score,
                "in_degree": m.in_degree,
                "out_degree": m.out_degree,
                "workflow_count": m.workflow_count,
                "service_count": m.service_count,
                "critical_path_count": m.critical_path_count,
            }

        return idx

    # ══════════════════════════════════════════════════════════════════
    # 1. Critical Component Detector
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _compute_influence(idx: _GraphIndex, nid: str) -> float:
        """0–100 influence score based on fan-in, fan-out, centrality, weight."""
        fi = idx.in_degree(nid)
        fo = idx.out_degree(nid)

        # Weighted edge contribution (sum of incoming weights)
        weight_sum = sum(w for _, _, w in idx.rev.get(nid, []))

        # Centrality from pre-computed metrics (if available)
        metrics = idx.metrics.get(nid, {})
        centrality = metrics.get("centrality_score", 0.0)

        # Normalize
        max_fi = max((idx.in_degree(n) for n in idx.nodes), default=1) or 1
        max_fo = max((idx.out_degree(n) for n in idx.nodes), default=1) or 1
        max_weight = max(
            (sum(w for _, _, w in idx.rev.get(n, [])) for n in idx.nodes),
            default=1.0,
        ) or 1.0

        fi_norm = min(1.0, fi / max_fi)
        fo_norm = min(1.0, fo / max_fo)
        w_norm = min(1.0, weight_sum / max_weight)
        c_norm = centrality / 100.0

        score = (
            fi_norm * 35
            + fo_norm * 25
            + w_norm * 15
            + c_norm * 25
        )
        return round(min(100.0, max(0.0, score)), 2)

    async def detect_critical_components(
        self, repo_id: UUID, db: AsyncSession
    ) -> CriticalComponentsResponse:
        idx = await self._load_index(repo_id, db)

        scored: list[tuple[str, float]] = []
        for nid in idx.nodes:
            score = self._compute_influence(idx, nid)
            scored.append((nid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:MAX_RESULTS]

        components = []
        for nid, score in top:
            meta = idx.nodes[nid]
            fi = idx.in_degree(nid)
            fo = idx.out_degree(nid)
            # Dependents = unique nodes that depend on this node (incoming edges)
            dependents = {src for src, _, _ in idx.rev.get(nid, [])}

            parts = []
            if fi >= FAN_IN_EXPLOSION:
                parts.append(f"high fan-in ({fi} callers)")
            if fo >= FAN_OUT_EXPLOSION:
                parts.append(f"high fan-out ({fo} dependencies)")
            if score >= 70:
                parts.append("central architectural hub")
            elif score >= 40:
                parts.append("significant influence on the system")
            else:
                parts.append("moderate influence")

            components.append(CriticalComponent(
                node_id=nid,
                name=meta["name"],
                node_type=meta["node_type"],
                file_path=meta.get("file_path"),
                influence_score=score,
                fan_in=fi,
                fan_out=fo,
                dependents_count=len(dependents),
                reason="; ".join(parts),
            ))

        return CriticalComponentsResponse(
            repo_id=str(repo_id),
            components=components,
            total_nodes=idx.total_nodes,
            total_edges=idx.total_edges,
        )

    # ══════════════════════════════════════════════════════════════════
    # 2. Bottleneck Detector
    # ══════════════════════════════════════════════════════════════════

    async def detect_bottlenecks(
        self, repo_id: UUID, db: AsyncSession
    ) -> BottlenecksResponse:
        idx = await self._load_index(repo_id, db)
        bottlenecks: list[Bottleneck] = []

        god_count = 0
        oversized_count = 0
        fan_count = 0

        for nid, meta in idx.nodes.items():
            fi = idx.in_degree(nid)
            fo = idx.out_degree(nid)

            # God Service: very high fan-out
            if fo >= GOD_SERVICE_FAN_OUT and meta["node_type"] in ("service", "class", "function", "method"):
                god_count += 1
                bottlenecks.append(Bottleneck(
                    node_id=nid,
                    name=meta["name"],
                    node_type=meta["node_type"],
                    file_path=meta.get("file_path"),
                    bottleneck_type="god_service",
                    severity="critical" if fo >= GOD_SERVICE_FAN_OUT * 2 else "high",
                    metric_value=float(fo),
                    threshold=float(GOD_SERVICE_FAN_OUT),
                    description=(
                        f"'{meta['name']}' has {fo} outgoing dependencies — "
                        f"classic God Service pattern. Should be decomposed."
                    ),
                ))

            # Fan-in explosion
            if fi >= FAN_IN_EXPLOSION:
                fan_count += 1
                bottlenecks.append(Bottleneck(
                    node_id=nid,
                    name=meta["name"],
                    node_type=meta["node_type"],
                    file_path=meta.get("file_path"),
                    bottleneck_type="fan_in_explosion",
                    severity="critical" if fi >= FAN_IN_EXPLOSION * 2 else "high",
                    metric_value=float(fi),
                    threshold=float(FAN_IN_EXPLOSION),
                    description=(
                        f"'{meta['name']}' is called by {fi} components — "
                        f"changes here have massive blast radius."
                    ),
                ))

            # Fan-out explosion
            if fo >= FAN_OUT_EXPLOSION and meta["node_type"] not in ("service", "class"):
                fan_count += 1
                bottlenecks.append(Bottleneck(
                    node_id=nid,
                    name=meta["name"],
                    node_type=meta["node_type"],
                    file_path=meta.get("file_path"),
                    bottleneck_type="fan_out_explosion",
                    severity="high" if fo >= FAN_OUT_EXPLOSION * 2 else "medium",
                    metric_value=float(fo),
                    threshold=float(FAN_OUT_EXPLOSION),
                    description=(
                        f"'{meta['name']}' depends on {fo} components — "
                        f"fragile to cascading changes."
                    ),
                ))

        # Oversized modules (files with too many nodes)
        for fpath, nids in idx.by_file.items():
            if len(nids) >= OVERSIZED_MODULE_NODES:
                oversized_count += 1
                # Pick the highest-influence node in the file as representative
                rep_nid = max(nids, key=lambda n: self._compute_influence(idx, n))
                meta = idx.nodes[rep_nid]
                bottlenecks.append(Bottleneck(
                    node_id=rep_nid,
                    name=fpath.rsplit("/", 1)[-1] if "/" in fpath else fpath,
                    node_type="module",
                    file_path=fpath,
                    bottleneck_type="oversized_module",
                    severity="high" if len(nids) >= OVERSIZED_MODULE_NODES * 2 else "medium",
                    metric_value=float(len(nids)),
                    threshold=float(OVERSIZED_MODULE_NODES),
                    description=(
                        f"File '{fpath}' contains {len(nids)} nodes — "
                        f"exceeds cohesion threshold. Consider splitting."
                    ),
                ))

        # Sort by severity then metric value
        severity_order = {"critical": 0, "high": 1, "medium": 2}
        bottlenecks.sort(key=lambda b: (severity_order.get(b.severity, 9), -b.metric_value))
        bottlenecks = bottlenecks[:MAX_RESULTS]

        return BottlenecksResponse(
            repo_id=str(repo_id),
            bottlenecks=bottlenecks,
            total_god_services=god_count,
            total_oversized_modules=oversized_count,
            total_fan_explosions=fan_count,
        )

    # ══════════════════════════════════════════════════════════════════
    # 3. Refactor Opportunity Engine
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _detect_cycles(idx: _GraphIndex) -> list[CyclicDependency]:
        """Tarjan's SCC algorithm to find strongly-connected components (cycles)."""
        index_counter = [0]
        stack: list[str] = []
        lowlink: dict[str, int] = {}
        index: dict[str, int] = {}
        on_stack: set[str] = set()
        sccs: list[list[str]] = []

        def strongconnect(v: str) -> None:
            index[v] = index_counter[0]
            lowlink[v] = index_counter[0]
            index_counter[0] += 1
            stack.append(v)
            on_stack.add(v)

            for nb, _etype, _w in idx.fwd.get(v, []):
                if nb not in index:
                    strongconnect(nb)
                    lowlink[v] = min(lowlink[v], lowlink[nb])
                elif nb in on_stack:
                    lowlink[v] = min(lowlink[v], index[nb])

            if lowlink[v] == index[v]:
                scc: list[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    scc.append(w)
                    if w == v:
                        break
                if len(scc) > 1:
                    sccs.append(scc)

        # Use iterative approach for large graphs to avoid recursion limits
        for nid in idx.nodes:
            if nid not in index:
                # Iterative Tarjan's
                call_stack: list[tuple[str, int]] = [(nid, 0)]
                index[nid] = index_counter[0]
                lowlink[nid] = index_counter[0]
                index_counter[0] += 1
                stack.append(nid)
                on_stack.add(nid)

                while call_stack:
                    v, ni = call_stack[-1]
                    neighbors = idx.fwd.get(v, [])

                    if ni < len(neighbors):
                        call_stack[-1] = (v, ni + 1)
                        nb = neighbors[ni][0]
                        if nb not in index:
                            index[nb] = index_counter[0]
                            lowlink[nb] = index_counter[0]
                            index_counter[0] += 1
                            stack.append(nb)
                            on_stack.add(nb)
                            call_stack.append((nb, 0))
                        elif nb in on_stack:
                            lowlink[v] = min(lowlink[v], index[nb])
                    else:
                        if lowlink[v] == index[v]:
                            scc: list[str] = []
                            while True:
                                w = stack.pop()
                                on_stack.discard(w)
                                scc.append(w)
                                if w == v:
                                    break
                            if len(scc) > 1:
                                sccs.append(scc)

                        call_stack.pop()
                        if call_stack:
                            parent = call_stack[-1][0]
                            lowlink[parent] = min(lowlink[parent], lowlink[v])

        cycles: list[CyclicDependency] = []
        for i, scc in enumerate(sccs):
            if len(scc) > MAX_CYCLE_LENGTH:
                scc = scc[:MAX_CYCLE_LENGTH]
            severity = "critical" if len(scc) >= 5 else ("high" if len(scc) >= 3 else "medium")
            cycles.append(CyclicDependency(
                cycle_id=i,
                nodes=[
                    {
                        "node_id": n,
                        "name": idx.nodes[n]["name"],
                        "node_type": idx.nodes[n]["node_type"],
                    }
                    for n in scc
                ],
                length=len(scc),
                severity=severity,
            ))

        cycles.sort(key=lambda c: (-c.length, c.cycle_id))
        return cycles[:MAX_RESULTS]

    @staticmethod
    def _detect_coupling(idx: _GraphIndex) -> list[CouplingPair]:
        """Find tightly coupled node pairs (bidirectional or many shared edges)."""
        pair_edges: dict[tuple[str, str], int] = defaultdict(int)

        for (f, t), etypes in idx.edge_types.items():
            canonical = (min(f, t), max(f, t))
            pair_edges[canonical] += len(etypes)

        pairs: list[CouplingPair] = []
        for (a, b), count in pair_edges.items():
            if count < TIGHT_COUPLING_EDGE_THRESHOLD:
                continue
            # Check bidirectionality
            ab_types = idx.edge_types.get((a, b), set())
            ba_types = idx.edge_types.get((b, a), set())
            is_bidirectional = bool(ab_types) and bool(ba_types)
            total = len(ab_types) + len(ba_types)

            coupling_score = min(100.0, total * 15.0 + (20.0 if is_bidirectional else 0.0))
            rec = (
                "Extract a shared interface or event bus to decouple these components."
                if is_bidirectional
                else "Consolidate interactions — consider merging or introducing a mediator."
            )

            pairs.append(CouplingPair(
                node_a_id=a,
                node_a_name=idx.nodes[a]["name"],
                node_b_id=b,
                node_b_name=idx.nodes[b]["name"],
                shared_edges=total,
                coupling_score=round(coupling_score, 2),
                recommendation=rec,
            ))

        pairs.sort(key=lambda p: -p.coupling_score)
        return pairs[:MAX_RESULTS]

    @staticmethod
    def _detect_violations(idx: _GraphIndex) -> list[ArchitectureViolation]:
        """Detect layer-skip and bidirectional coupling violations."""
        violations: list[ArchitectureViolation] = []
        seen_bi: set[tuple[str, str]] = set()

        for (f, t), etypes in idx.edge_types.items():
            f_meta = idx.nodes.get(f, {})
            t_meta = idx.nodes.get(t, {})
            f_layer = LAYER_ORDER.get(f_meta.get("node_type", ""), None)
            t_layer = LAYER_ORDER.get(t_meta.get("node_type", ""), None)

            # Layer-skip: jumping more than 1 level
            if f_layer is not None and t_layer is not None and abs(f_layer - t_layer) > 1:
                # Only report if going upward (dependency inversion) or large skip
                violations.append(ArchitectureViolation(
                    violation_type="layer_skip",
                    description=(
                        f"'{f_meta.get('name', f)}' ({f_meta.get('node_type', '?')}) directly "
                        f"accesses '{t_meta.get('name', t)}' ({t_meta.get('node_type', '?')}) — "
                        f"skipping {abs(f_layer - t_layer) - 1} layer(s)."
                    ),
                    severity="high" if abs(f_layer - t_layer) > 2 else "medium",
                    involved_nodes=[
                        {"node_id": f, "name": f_meta.get("name", f), "node_type": f_meta.get("node_type", "?")},
                        {"node_id": t, "name": t_meta.get("name", t), "node_type": t_meta.get("node_type", "?")},
                    ],
                ))

            # Bidirectional coupling
            canonical = (min(f, t), max(f, t))
            if canonical not in seen_bi and (t, f) in idx.edge_types:
                seen_bi.add(canonical)
                violations.append(ArchitectureViolation(
                    violation_type="bidirectional_coupling",
                    description=(
                        f"'{f_meta.get('name', f)}' and '{t_meta.get('name', t)}' "
                        f"depend on each other — introduces circular risk."
                    ),
                    severity="high",
                    involved_nodes=[
                        {"node_id": f, "name": f_meta.get("name", f), "node_type": f_meta.get("node_type", "?")},
                        {"node_id": t, "name": t_meta.get("name", t), "node_type": t_meta.get("node_type", "?")},
                    ],
                ))

        violations.sort(key=lambda v: {"critical": 0, "high": 1, "medium": 2}.get(v.severity, 9))
        return violations[:MAX_RESULTS]

    async def find_refactor_opportunities(
        self, repo_id: UUID, db: AsyncSession
    ) -> RefactorOpportunitiesResponse:
        idx = await self._load_index(repo_id, db)

        cycles = self._detect_cycles(idx)
        coupling = self._detect_coupling(idx)
        violations = self._detect_violations(idx)

        return RefactorOpportunitiesResponse(
            repo_id=str(repo_id),
            cyclic_dependencies=cycles,
            tightly_coupled=coupling,
            violations=violations,
            total_issues=len(cycles) + len(coupling) + len(violations),
        )

    # ══════════════════════════════════════════════════════════════════
    # 4. Change Risk Predictor
    # ══════════════════════════════════════════════════════════════════

    async def predict_change_risk(
        self, repo_id: UUID, node_id: str, db: AsyncSession
    ) -> ChangeRiskReport | None:
        idx = await self._load_index(repo_id, db)

        if node_id not in idx.nodes:
            return None

        meta = idx.nodes[node_id]

        # BFS from the target node (reverse — find everything that depends on it)
        visited: dict[str, int] = {node_id: 0}
        frontier = [node_id]
        depth = 0

        while frontier and depth < MAX_BFS_DEPTH:
            depth += 1
            next_frontier: list[str] = []
            for nid in frontier:
                for src, _etype, _w in idx.rev.get(nid, []):
                    if src not in visited:
                        visited[src] = depth
                        next_frontier.append(src)
            frontier = next_frontier

        # Categorize impacted nodes
        impacted_nodes: list[ImpactedEntity] = []
        impacted_apis: list[ImpactedEntity] = []
        impacted_services: list[ImpactedEntity] = []
        impacted_dbs: list[ImpactedEntity] = []

        for nid, dist in visited.items():
            if nid == node_id:
                continue
            nmeta = idx.nodes.get(nid, {})
            entity = ImpactedEntity(
                node_id=nid,
                name=nmeta.get("name", nid[:8]),
                node_type=nmeta.get("node_type", "unknown"),
                file_path=nmeta.get("file_path"),
                impact_path_length=dist,
            )
            impacted_nodes.append(entity)

            ntype = nmeta.get("node_type", "")
            if ntype == "api_route":
                impacted_apis.append(entity)
            elif ntype == "service":
                impacted_services.append(entity)
            elif ntype == "database_table":
                impacted_dbs.append(entity)

        # Also check forward for database impacts (what this node writes to)
        for tgt, etype, _w in idx.fwd.get(node_id, []):
            tmeta = idx.nodes.get(tgt, {})
            if tmeta.get("node_type") == "database_table" and tgt not in visited:
                impacted_dbs.append(ImpactedEntity(
                    node_id=tgt,
                    name=tmeta.get("name", tgt[:8]),
                    node_type="database_table",
                    file_path=tmeta.get("file_path"),
                    impact_path_length=1,
                ))

        total = len(impacted_nodes)

        # Risk score: weighted by blast radius, APIs affected, DB writes
        risk_raw = (
            min(1.0, total / 50) * 40
            + min(1.0, len(impacted_apis) / 10) * 25
            + min(1.0, len(impacted_services) / 8) * 15
            + min(1.0, len(impacted_dbs) / 5) * 20
        )
        risk_score = round(min(100.0, max(0.0, risk_raw)), 2)

        if risk_score >= 75:
            risk_level = "critical"
        elif risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Build summary
        parts = []
        if impacted_apis:
            parts.append(f"{len(impacted_apis)} API(s)")
        if impacted_services:
            parts.append(f"{len(impacted_services)} service(s)")
        if impacted_dbs:
            parts.append(f"{len(impacted_dbs)} database(s)")
        parts.append(f"{total} total node(s)")

        summary = (
            f"Modifying '{meta['name']}' impacts {', '.join(parts)}. "
            f"Risk level: {risk_level} ({risk_score}/100)."
        )

        # Sort all lists by path length
        for lst in (impacted_nodes, impacted_apis, impacted_services, impacted_dbs):
            lst.sort(key=lambda e: (e.impact_path_length, e.name))

        return ChangeRiskReport(
            repo_id=str(repo_id),
            target_node_id=node_id,
            target_node_name=meta["name"],
            risk_score=risk_score,
            risk_level=risk_level,
            impacted_nodes=impacted_nodes[:MAX_RESULTS],
            impacted_apis=impacted_apis[:MAX_RESULTS],
            impacted_services=impacted_services[:MAX_RESULTS],
            impacted_databases=impacted_dbs[:MAX_RESULTS],
            total_impacted=total,
            summary=summary,
        )

    # ══════════════════════════════════════════════════════════════════
    # 5. Architecture Findings Generator
    # ══════════════════════════════════════════════════════════════════

    async def generate_findings(
        self, repo_id: UUID, db: AsyncSession
    ) -> FindingsResponse:
        idx = await self._load_index(repo_id, db)
        raw_findings: list[tuple[float, Finding]] = []  # (sort_key, Finding)

        # ── Finding sources ──

        # A) Critical hubs
        for nid in idx.nodes:
            score = self._compute_influence(idx, nid)
            if score >= 60:
                meta = idx.nodes[nid]
                raw_findings.append((
                    -score,
                    Finding(
                        rank=0,
                        title=f"Critical Hub: {meta['name']}",
                        category="critical_component",
                        severity="critical" if score >= 80 else "high",
                        description=(
                            f"'{meta['name']}' ({meta['node_type']}) has an influence score of "
                            f"{score}/100. It is a central architectural hub — changes here have "
                            f"wide-reaching impact."
                        ),
                        related_node_ids=[nid],
                        metric_name="influence_score",
                        metric_value=score,
                        recommendation=(
                            "Add comprehensive tests, introduce an abstraction layer, "
                            "and document change procedures for this critical component."
                        ),
                    ),
                ))

        # B) God services
        for nid, meta in idx.nodes.items():
            fo = idx.out_degree(nid)
            if fo >= GOD_SERVICE_FAN_OUT:
                raw_findings.append((
                    -fo,
                    Finding(
                        rank=0,
                        title=f"God Service: {meta['name']}",
                        category="bottleneck",
                        severity="critical" if fo >= GOD_SERVICE_FAN_OUT * 2 else "high",
                        description=(
                            f"'{meta['name']}' has {fo} outgoing dependencies — this is a God "
                            f"Service anti-pattern that violates the Single Responsibility Principle."
                        ),
                        related_node_ids=[nid],
                        metric_name="fan_out",
                        metric_value=float(fo),
                        recommendation=(
                            "Break this component into smaller, focused services. "
                            "Extract cohesive groups of dependencies into sub-services."
                        ),
                    ),
                ))

        # C) Cyclic dependencies
        cycles = self._detect_cycles(idx)
        for cyc in cycles[:3]:
            raw_findings.append((
                -cyc.length * 10,
                Finding(
                    rank=0,
                    title=f"Cyclic Dependency ({cyc.length} nodes)",
                    category="coupling",
                    severity=cyc.severity,
                    description=(
                        f"A dependency cycle of {cyc.length} nodes was detected: "
                        + " → ".join(n["name"] for n in cyc.nodes[:5])
                        + ("…" if cyc.length > 5 else "")
                        + ". Cycles prevent independent deployment and testing."
                    ),
                    related_node_ids=[n["node_id"] for n in cyc.nodes],
                    metric_name="cycle_length",
                    metric_value=float(cyc.length),
                    recommendation=(
                        "Break the cycle by introducing an interface, event, or "
                        "dependency inversion at the weakest coupling point."
                    ),
                ),
            ))

        # D) Fan-in explosion
        for nid, meta in idx.nodes.items():
            fi = idx.in_degree(nid)
            if fi >= FAN_IN_EXPLOSION:
                raw_findings.append((
                    -fi,
                    Finding(
                        rank=0,
                        title=f"High Fan-In: {meta['name']}",
                        category="risk",
                        severity="high" if fi >= FAN_IN_EXPLOSION * 2 else "medium",
                        description=(
                            f"'{meta['name']}' is depended on by {fi} other components. "
                            f"Any change here has massive blast radius."
                        ),
                        related_node_ids=[nid],
                        metric_name="fan_in",
                        metric_value=float(fi),
                        recommendation=(
                            "Ensure thorough test coverage. Consider adding a "
                            "façade to isolate callers from internal changes."
                        ),
                    ),
                ))

        # E) Oversized modules
        for fpath, nids in idx.by_file.items():
            if len(nids) >= OVERSIZED_MODULE_NODES:
                raw_findings.append((
                    -len(nids),
                    Finding(
                        rank=0,
                        title=f"Oversized Module: {fpath.rsplit('/', 1)[-1] if '/' in fpath else fpath}",
                        category="health",
                        severity="high" if len(nids) >= OVERSIZED_MODULE_NODES * 2 else "medium",
                        description=(
                            f"'{fpath}' contains {len(nids)} graph nodes — well above the "
                            f"cohesion threshold of {OVERSIZED_MODULE_NODES}."
                        ),
                        related_node_ids=nids[:5],
                        metric_name="node_count",
                        metric_value=float(len(nids)),
                        recommendation=(
                            "Split into smaller files grouped by feature or responsibility. "
                            "Large files are harder to review, test, and maintain."
                        ),
                    ),
                ))

        # Sort deterministically and pick top 10
        raw_findings.sort(key=lambda x: (x[0], x[1].title))
        findings: list[Finding] = []
        for i, (_, f) in enumerate(raw_findings[:MAX_FINDINGS]):
            f.rank = i + 1
            findings.append(f)

        return FindingsResponse(
            repo_id=str(repo_id),
            findings=findings,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # ══════════════════════════════════════════════════════════════════
    # 6. Intelligence Dashboard (aggregated)
    # ══════════════════════════════════════════════════════════════════

    async def get_dashboard(
        self, repo_id: UUID, db: AsyncSession
    ) -> IntelligenceDashboard:
        idx = await self._load_index(repo_id, db)

        # ── Scores ──
        total_n = idx.total_nodes
        total_e = idx.total_edges

        if total_n == 0:
            return IntelligenceDashboard(
                repo_id=str(repo_id),
                architecture_score=100.0,
                risk_score=0.0,
                architecture_grade="A",
                total_nodes=0,
                total_edges=0,
                critical_components=[],
                bottlenecks=[],
                refactor_suggestions=[],
                top_findings=[],
            )

        # Architecture score: lower is worse
        # Penalties: cycles, high coupling, god services, oversized modules
        penalty = 0.0

        # Cycles
        cycles = self._detect_cycles(idx)
        penalty += min(25.0, len(cycles) * 5.0)

        # God services
        god_count = sum(
            1 for nid in idx.nodes
            if idx.out_degree(nid) >= GOD_SERVICE_FAN_OUT
        )
        penalty += min(20.0, god_count * 4.0)

        # Bidirectional couplings
        bi_count = 0
        seen: set[tuple[str, str]] = set()
        for (f, t) in idx.edge_types:
            canonical = (min(f, t), max(f, t))
            if canonical not in seen and (t, f) in idx.edge_types:
                seen.add(canonical)
                bi_count += 1
        penalty += min(15.0, bi_count * 2.0)

        # Graph density (too dense = hard to maintain)
        density = total_e / (total_n * max(total_n - 1, 1))
        penalty += min(15.0, density * 500)

        # Fan-in explosions
        fi_explosions = sum(
            1 for nid in idx.nodes if idx.in_degree(nid) >= FAN_IN_EXPLOSION
        )
        penalty += min(15.0, fi_explosions * 3.0)

        architecture_score = round(max(0.0, min(100.0, 100.0 - penalty)), 2)

        # Risk score: higher is riskier
        risk_raw = (
            min(1.0, god_count / 5) * 25
            + min(1.0, len(cycles) / 5) * 25
            + min(1.0, bi_count / 10) * 20
            + min(1.0, fi_explosions / 5) * 20
            + min(1.0, density * 100) * 10
        )
        risk_score = round(min(100.0, max(0.0, risk_raw)), 2)

        # Grade
        if architecture_score >= 90:
            grade = "A"
        elif architecture_score >= 75:
            grade = "B"
        elif architecture_score >= 60:
            grade = "C"
        elif architecture_score >= 40:
            grade = "D"
        else:
            grade = "F"

        # ── Sub-sections ──
        critical_resp = await self.detect_critical_components(repo_id, db)
        bottleneck_resp = await self.detect_bottlenecks(repo_id, db)
        findings_resp = await self.generate_findings(repo_id, db)

        # Refactor suggestions = findings in "coupling" or "bottleneck" category
        refactor_suggestions = [
            f for f in findings_resp.findings
            if f.category in ("coupling", "bottleneck")
        ]

        return IntelligenceDashboard(
            repo_id=str(repo_id),
            architecture_score=architecture_score,
            risk_score=risk_score,
            architecture_grade=grade,
            total_nodes=total_n,
            total_edges=total_e,
            critical_components=critical_resp.components[:10],
            bottlenecks=bottleneck_resp.bottlenecks[:10],
            refactor_suggestions=refactor_suggestions[:5],
            top_findings=findings_resp.findings[:10],
        )
