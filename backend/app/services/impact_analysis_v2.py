"""
Impact Radar V2 — Graph-First Impact Analysis

Architecture:
  Function → Graph Traversal → Blast Radius → Risk Engine → LLM Explanation

The graph is the source of truth. The LLM only explains findings.
"""

import asyncio
import json
import logging
import time
from collections import deque
from typing import Optional
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import Node, Edge, RepoFile
from app.schemas.repo_detail import (
    ImpactAnalysisRequest,
    ImpactEvidence,
    AffectedItemV2,
    BlastRadiusV2,
    RiskFactorV2,
    RiskResultV2,
    FuzzyMatch,
    ImpactReportV2,
)

logger = logging.getLogger(__name__)


# ── Step 1: Node Resolution ──────────────────────────

async def resolve_node(
    query: str,
    repo_id: UUID,
    db: AsyncSession,
) -> tuple[Optional[Node], list[FuzzyMatch]]:
    """Resolve a query string to an exact node, or return fuzzy matches."""

    # Try exact match first
    result = await db.execute(
        select(Node).where(Node.repo_id == repo_id, Node.name == query)
    )
    exact = result.scalars().all()
    if len(exact) == 1:
        return exact[0], []
    if len(exact) > 1:
        # Multiple exact matches — return best (prefer function over method)
        priority = {"function": 0, "api_route": 1, "method": 2, "class": 3}
        exact.sort(key=lambda n: priority.get(n.node_type, 99))
        return exact[0], [
            FuzzyMatch(
                node_id=str(n.id),
                name=n.name,
                node_type=n.node_type,
                file_path=n.full_path.split(":")[0] if n.full_path else "",
                score=1.0,
            )
            for n in exact[1:]
        ]

    # Fuzzy match — ILIKE search
    result = await db.execute(
        select(Node)
        .where(Node.repo_id == repo_id, Node.name.ilike(f"%{query}%"))
        .limit(10)
    )
    fuzzy = result.scalars().all()
    if fuzzy:
        return fuzzy[0], [
            FuzzyMatch(
                node_id=str(n.id),
                name=n.name,
                node_type=n.node_type,
                file_path=n.full_path.split(":")[0] if n.full_path else "",
                score=0.7,
            )
            for n in fuzzy[1:]
        ]

    return None, []


# ── Step 2: Graph Traversal (BFS, depth ≤ 5) ─────────

class TraversalResult:
    """Collects all graph findings during BFS traversal."""

    def __init__(self):
        self.direct_callers: list[tuple[Node, ImpactEvidence]] = []
        self.indirect_callers: list[tuple[Node, ImpactEvidence]] = []
        self.affected_apis: list[tuple[Node, ImpactEvidence]] = []
        self.affected_tables: list[tuple[Node, ImpactEvidence]] = []
        self.affected_services: list[tuple[Node, ImpactEvidence]] = []
        self.affected_files: set[str] = set()
        self.affected_classes: list[tuple[Node, ImpactEvidence]] = []
        self.affected_auth: list[tuple[Node, ImpactEvidence]] = []
        self.all_affected_ids: set[UUID] = set()
        self.cycles_detected: int = 0
        self.imports_count: int = 0


async def traverse_graph(
    source_node: Node,
    repo_id: UUID,
    db: AsyncSession,
    max_depth: int = 5,
) -> TraversalResult:
    """
    BFS traversal from source node upstream (who depends on this node?).
    Collects callers, APIs, tables, services, auth deps, classes, files.
    Uses a visited set to avoid cycles.
    """
    result = TraversalResult()
    visited: set[UUID] = {source_node.id}
    # Queue items: (node_id, current_depth, evidence_chain)
    queue: deque[tuple[UUID, int, list[str]]] = deque()

    # Seed: find all nodes that directly reference the source node
    # i.e. edges WHERE to_node_id == source_node.id (inbound edges = who calls/uses this)
    queue.append((source_node.id, 0, [source_node.name]))

    # Also collect outbound edges from the source for tables/services/auth
    await _collect_outbound(source_node, repo_id, db, result, [source_node.name])

    while queue:
        current_id, depth, chain = queue.popleft()
        if depth >= max_depth:
            continue

        # Find all inbound edges to current_id
        FromNode = aliased(Node)
        inbound_res = await db.execute(
            select(Edge.edge_type, FromNode)
            .join(FromNode, Edge.from_node_id == FromNode.id)
            .where(Edge.to_node_id == current_id, Edge.from_node_id != current_id)
        )
        inbound_edges = inbound_res.all()

        for edge_type, caller_node in inbound_edges:
            if caller_node.id in visited:
                result.cycles_detected += 1
                continue

            visited.add(caller_node.id)
            result.all_affected_ids.add(caller_node.id)

            new_chain = chain + [caller_node.name]
            evidence = ImpactEvidence(
                source=caller_node.name,
                target=chain[-1],
                edge_type=edge_type,
                depth=depth + 1,
                chain=new_chain,
            )

            file_path = caller_node.full_path.split(":")[0] if caller_node.full_path else ""
            result.affected_files.add(file_path)

            # Classify the caller
            if caller_node.node_type == "api_route":
                result.affected_apis.append((caller_node, evidence))
            elif caller_node.node_type == "class":
                result.affected_classes.append((caller_node, evidence))
            elif edge_type in ("auth_dependency", "dependency_injection"):
                result.affected_auth.append((caller_node, evidence))
            elif depth == 0:
                result.direct_callers.append((caller_node, evidence))
            else:
                result.indirect_callers.append((caller_node, evidence))

            # Also collect outbound edges from this caller (tables, services, etc.)
            await _collect_outbound(caller_node, repo_id, db, result, new_chain)

            # Continue BFS upstream
            queue.append((caller_node.id, depth + 1, new_chain))

    return result


async def _collect_outbound(
    node: Node,
    repo_id: UUID,
    db: AsyncSession,
    result: TraversalResult,
    chain: list[str],
) -> None:
    """Collect outbound relationships: tables, services, auth from a node."""
    ToNode = aliased(Node)
    outbound_res = await db.execute(
        select(Edge.edge_type, ToNode)
        .join(ToNode, Edge.to_node_id == ToNode.id)
        .where(Edge.from_node_id == node.id)
    )

    for edge_type, target_node in outbound_res.all():
        if target_node.id in result.all_affected_ids and edge_type not in (
            "reads_table", "writes_table", "updates_table", "deletes_table",
            "uses_service", "auth_dependency", "imports",
        ):
            continue

        evidence = ImpactEvidence(
            source=node.name,
            target=target_node.name,
            edge_type=edge_type,
            depth=0,
            chain=chain + [target_node.name],
        )

        if edge_type in ("reads_table", "writes_table", "updates_table", "deletes_table"):
            # Deduplicate tables by name
            existing_names = {t[0].name for t in result.affected_tables}
            if target_node.name not in existing_names:
                result.affected_tables.append((target_node, evidence))
        elif edge_type == "uses_service":
            existing_names = {s[0].name for s in result.affected_services}
            if target_node.name not in existing_names:
                result.affected_services.append((target_node, evidence))
        elif edge_type in ("auth_dependency", "dependency_injection"):
            existing_names = {a[0].name for a in result.affected_auth}
            if target_node.name not in existing_names:
                result.affected_auth.append((target_node, evidence))
        elif edge_type == "imports":
            result.imports_count += 1


# ── Step 3: Blast Radius ─────────────────────────────

def compute_blast_radius(traversal: TraversalResult) -> BlastRadiusV2:
    return BlastRadiusV2(
        direct_dependents=len(traversal.direct_callers),
        indirect_dependents=len(traversal.indirect_callers),
        api_impact=len(traversal.affected_apis),
        database_impact=len(traversal.affected_tables),
        service_impact=len(traversal.affected_services),
        file_impact=len(traversal.affected_files),
        auth_impact=len(traversal.affected_auth),
        class_impact=len(traversal.affected_classes),
        total_nodes_affected=len(traversal.all_affected_ids),
        cycles_detected=traversal.cycles_detected,
    )


# ── Step 4: Risk Engine ──────────────────────────────

def compute_risk(
    scenario: str,
    blast: BlastRadiusV2,
    imports_count: int = 0,
) -> RiskResultV2:
    """
    Scenario-specific risk formulas. Score clamped 0-100.
    """
    factors: list[RiskFactorV2] = []

    if scenario == "delete":
        _add_factor(factors, "Direct dependents", blast.direct_dependents, 5)
        _add_factor(factors, "Indirect dependents", blast.indirect_dependents, 2)
        _add_factor(factors, "API exposure", blast.api_impact, 10)
        _add_factor(factors, "Database usage", blast.database_impact, 8)
        _add_factor(factors, "Auth dependencies", blast.auth_impact, 10)
    elif scenario == "modify":
        _add_factor(factors, "Direct dependents", blast.direct_dependents, 3)
        _add_factor(factors, "Indirect dependents", blast.indirect_dependents, 1)
        _add_factor(factors, "API exposure", blast.api_impact, 6)
        _add_factor(factors, "Database usage", blast.database_impact, 5)
    elif scenario == "rename":
        _add_factor(factors, "Direct dependents", blast.direct_dependents, 2)
        _add_factor(factors, "API exposure", blast.api_impact, 5)
    elif scenario == "move":
        _add_factor(factors, "Direct dependents", blast.direct_dependents, 3)
        _add_factor(factors, "Import references", imports_count, 5)
    else:
        # Fallback to delete formula
        _add_factor(factors, "Direct dependents", blast.direct_dependents, 5)
        _add_factor(factors, "API exposure", blast.api_impact, 10)

    raw_score = sum(f.contribution for f in factors)
    score = max(0, min(100, raw_score))

    if score <= 20:
        level = "Safe"
    elif score <= 40:
        level = "Low"
    elif score <= 60:
        level = "Medium"
    elif score <= 80:
        level = "High"
    else:
        level = "Critical"

    return RiskResultV2(
        score=score,
        level=level,
        scenario=scenario,
        factors=factors,
    )


def _add_factor(
    factors: list[RiskFactorV2], name: str, count: int, weight: int
) -> None:
    factors.append(
        RiskFactorV2(
            factor=name,
            count=count,
            weight=weight,
            contribution=count * weight,
        )
    )


# ── Step 5: LLM Explanation ──────────────────────────

async def generate_llm_explanation(
    query: str,
    scenario: str,
    node_name: str,
    node_type: str,
    risk: RiskResultV2,
    blast: BlastRadiusV2,
    direct_callers: list[AffectedItemV2],
    affected_apis: list[AffectedItemV2],
    affected_tables: list[AffectedItemV2],
    affected_services: list[AffectedItemV2],
    affected_auth: list[AffectedItemV2],
    affected_files: list[str],
) -> dict:
    """
    Use Groq LLM to EXPLAIN graph findings.
    The LLM receives pre-computed data and must not invent dependencies.
    """
    try:
        from app.utils.groq_client import groq_client

        graph_data = {
            "target_function": node_name,
            "target_type": node_type,
            "scenario": scenario,
            "risk_score": risk.score,
            "risk_level": risk.level,
            "risk_factors": [
                {"factor": f.factor, "count": f.count, "contribution": f.contribution}
                for f in risk.factors
            ],
            "blast_radius": {
                "direct_dependents": blast.direct_dependents,
                "indirect_dependents": blast.indirect_dependents,
                "api_impact": blast.api_impact,
                "database_impact": blast.database_impact,
                "service_impact": blast.service_impact,
                "file_impact": blast.file_impact,
                "auth_impact": blast.auth_impact,
                "total_affected": blast.total_nodes_affected,
            },
            "direct_callers": [c.name for c in direct_callers[:15]],
            "affected_apis": [
                {"name": a.name, "evidence": a.evidence.chain} for a in affected_apis[:10]
            ],
            "affected_tables": [
                {"name": t.name, "evidence": t.evidence.chain} for t in affected_tables[:10]
            ],
            "affected_services": [
                {"name": s.name, "evidence": s.evidence.chain} for s in affected_services[:10]
            ],
            "affected_auth": [a.name for a in affected_auth[:10]],
            "affected_files": affected_files[:20],
        }

        prompt = f"""You are an engineering architect analyzing the impact of a code change.

SCENARIO: {scenario.upper()} the function "{node_name}"

You MUST explain the impact using ONLY the supplied graph data below.
Do NOT invent dependencies. Do NOT guess. Every claim must be backed by the data.

GRAPH DATA:
{json.dumps(graph_data, indent=2)}

Respond with ONLY a JSON object containing these keys:
- executive_summary: A 2-3 sentence summary of the impact
- business_impact: Array of 2-4 business-level impact statements
- developer_impact: Array of 3-5 specific developer actions needed
- recommended_tests: Array of 3-6 specific test recommendations
- deployment_recommendation: One sentence deployment advice
- rollback_strategy: One sentence rollback plan

Be specific. Reference actual function names, API paths, and table names from the data.
Do NOT add any markdown, code fences, or explanations outside the JSON.
"""

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.1,
            ),
        )

        text = response.choices[0].message.content.strip()

        # Clean markdown fences
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start : end + 1]

        data = json.loads(text)
        return {
            "executive_summary": str(data.get("executive_summary", "")),
            "business_impact": [str(b) for b in data.get("business_impact", [])],
            "developer_impact": [str(d) for d in data.get("developer_impact", [])],
            "recommended_tests": [str(t) for t in data.get("recommended_tests", [])],
            "deployment_recommendation": str(data.get("deployment_recommendation", "")),
            "rollback_strategy": str(data.get("rollback_strategy", "")),
        }

    except Exception as e:
        logger.warning("LLM explanation failed: %s", e)
        return {
            "executive_summary": f"Graph analysis shows {scenario}ing '{node_name}' affects {blast.total_nodes_affected} nodes with risk level {risk.level}.",
            "business_impact": [],
            "developer_impact": [],
            "recommended_tests": [],
            "deployment_recommendation": "Review all affected dependencies before deploying.",
            "rollback_strategy": "Revert the commit and redeploy the previous version.",
        }


# ── Main Entry Point ─────────────────────────────────

def _make_affected_item(node: Node, evidence: ImpactEvidence) -> AffectedItemV2:
    return AffectedItemV2(
        name=node.name,
        node_type=node.node_type,
        file_path=node.full_path.split(":")[0] if node.full_path else "",
        evidence=evidence,
    )


async def run_impact_analysis(
    request: ImpactAnalysisRequest,
    repo_id: UUID,
    db: AsyncSession,
) -> ImpactReportV2:
    """
    Full Impact Radar V2 pipeline:
    1. Resolve node
    2. Graph traversal (BFS, depth ≤ 5)
    3. Blast radius
    4. Risk engine (scenario-specific)
    5. LLM explanation
    """
    start_time = time.time()

    # Step 1: Resolve
    node, fuzzy_matches = await resolve_node(request.query, repo_id, db)

    if not node:
        return ImpactReportV2(
            query=request.query,
            scenario=request.scenario,
            fuzzy_matches=fuzzy_matches,
            blast_radius=BlastRadiusV2(
                direct_dependents=0, indirect_dependents=0, api_impact=0,
                database_impact=0, service_impact=0, file_impact=0,
                auth_impact=0, class_impact=0, total_nodes_affected=0,
                cycles_detected=0,
            ),
            risk=RiskResultV2(score=0, level="Safe", scenario=request.scenario, factors=[]),
            executive_summary=f"No node found matching '{request.query}'. Try a different name.",
            analysis_time_ms=int((time.time() - start_time) * 1000),
        )

    # Step 2: Graph Traversal
    traversal = await traverse_graph(node, repo_id, db, max_depth=5)

    # Step 3: Blast Radius
    blast = compute_blast_radius(traversal)

    # Step 4: Risk Engine
    risk = compute_risk(request.scenario, blast, imports_count=traversal.imports_count)

    # Build affected items with evidence
    direct_callers = [_make_affected_item(n, e) for n, e in traversal.direct_callers]
    indirect_callers = [_make_affected_item(n, e) for n, e in traversal.indirect_callers]
    affected_apis = [_make_affected_item(n, e) for n, e in traversal.affected_apis]
    affected_tables = [_make_affected_item(n, e) for n, e in traversal.affected_tables]
    affected_services = [_make_affected_item(n, e) for n, e in traversal.affected_services]
    affected_classes = [_make_affected_item(n, e) for n, e in traversal.affected_classes]
    affected_auth = [_make_affected_item(n, e) for n, e in traversal.affected_auth]
    affected_files = sorted(traversal.affected_files)

    # Step 5: LLM Explanation
    llm_result = await generate_llm_explanation(
        query=request.query,
        scenario=request.scenario,
        node_name=node.name,
        node_type=node.node_type,
        risk=risk,
        blast=blast,
        direct_callers=direct_callers,
        affected_apis=affected_apis,
        affected_tables=affected_tables,
        affected_services=affected_services,
        affected_auth=affected_auth,
        affected_files=affected_files,
    )

    elapsed_ms = int((time.time() - start_time) * 1000)
    evidence_count = (
        len(direct_callers) + len(indirect_callers) + len(affected_apis)
        + len(affected_tables) + len(affected_services) + len(affected_auth)
    )

    return ImpactReportV2(
        query=request.query,
        scenario=request.scenario,
        resolved_node_id=str(node.id),
        resolved_node_name=node.name,
        resolved_node_type=node.node_type,
        resolved_file_path=node.full_path.split(":")[0] if node.full_path else "",
        fuzzy_matches=fuzzy_matches,
        blast_radius=blast,
        risk=risk,
        direct_callers=direct_callers,
        indirect_callers=indirect_callers,
        affected_apis=affected_apis,
        affected_tables=affected_tables,
        affected_services=affected_services,
        affected_files=affected_files,
        affected_classes=affected_classes,
        affected_auth=affected_auth,
        executive_summary=llm_result["executive_summary"],
        business_impact=llm_result["business_impact"],
        developer_impact=llm_result["developer_impact"],
        recommended_tests=llm_result["recommended_tests"],
        deployment_recommendation=llm_result["deployment_recommendation"],
        rollback_strategy=llm_result["rollback_strategy"],
        analysis_time_ms=elapsed_ms,
        graph_traversal_depth=5,
        evidence_count=evidence_count,
    )
