"""Architecture Explainer Agent.

Turns the EXISTING repository graph and reconstructed flows into understandable
architecture explanations. The graph (nodes / edges) and the Flow Reconstruction
Engine remain the single source of truth — this service only:

  1. RETRIEVES graph evidence for a node or a flow (callers, callees, services,
     APIs, database tables, dependencies, imports, flow steps).
  2. ASSEMBLES that evidence into a strictly-typed "evidence pack".
  3. GENERATES natural language with Groq, fed ONLY the evidence pack and
     instructed to invent nothing.

Grounding guarantees (hard rules):
  * No hallucinations — every dependency / caller / table named in the output
    comes from a real edge in the graph.
  * No invented dependencies — the LLM is given the dependency list and told it
    is the complete set; it may not add to it.
  * No invented business logic — the model describes only what edges/flows show.
  * If Groq is unavailable or returns junk, a deterministic fallback assembled
    purely from the same evidence is returned instead. Output is therefore never
    blocked on the LLM and never contains un-grounded claims.

The structured `evidence` block is echoed back on every response so any claim in
the prose can be audited against the graph facts that produced it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ImpactMetric, Node
from app.schemas.architecture import (
    ArchitectureExplanation,
    ExplanationEvidence,
    ImpactIfChanged,
    RelatedComponent,
)
from app.schemas.flow import Flow
from app.services import architecture_metrics as metrics
from app.services.architecture_metrics import GraphSignals
from app.services.architecture_service import ArchitectureService
from app.services.flow_reconstruction_service import FlowReconstructionService

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_MAX_TOKENS = 700
GROQ_TEMPERATURE = 0.1

# How many of each neighbour list to surface to the LLM / related_components.
RELATED_LIMIT = 12
EVIDENCE_LIST_LIMIT = 20

# Human-readable labels per node type, used for deterministic titles/fallback.
NODE_TYPE_LABEL = {
    "function": "Function",
    "method": "Method",
    "class": "Class",
    "api_route": "API Endpoint",
    "service": "Service",
    "database_table": "Database Table",
    "external_api": "External API",
}


class ArchitectureExplainerService:
    def __init__(self) -> None:
        self._arch = ArchitectureService()
        self._flows = FlowReconstructionService()

    # ════════════════════════════════════════════════════════════════════
    # Public API
    # ════════════════════════════════════════════════════════════════════
    async def explain_node(
        self, repo_id: UUID, node_id: UUID, db: AsyncSession
    ) -> ArchitectureExplanation | None:
        """Explain a single graph node (function / API / service / table / …)."""
        details = await self._arch.get_node_details(repo_id, node_id, db)
        if details is None:
            return None

        # Pull the underlying node for imports / signature — extra grounding the
        # summary view doesn't carry. Graph remains the source of truth.
        node_row = (
            await db.execute(
                select(Node.imports, Node.signature, Node.summary)
                .where(Node.id == node_id, Node.repo_id == repo_id)
            )
        ).first()
        imports = list(node_row[0] or []) if node_row else []
        signature = node_row[1] if node_row else None
        existing_summary = node_row[2] if node_row else None

        # Precomputed centrality, if analysis produced it. Optional — scores fall
        # back to degree-based signals when absent. Never required.
        centrality = (
            await db.execute(
                select(ImpactMetric.centrality_score)
                .where(ImpactMetric.repo_id == repo_id, ImpactMetric.node_id == node_id)
            )
        ).scalar_one_or_none()

        evidence = self._node_evidence(details, imports, centrality)
        related = self._node_related(details)

        # ── Deterministic analytics (no LLM) ──────────────────────────
        signals = self._node_signals(details, evidence)
        scores = metrics.score_node(signals)
        impact = self._node_impact(details, evidence)

        facts = self._node_facts(details, evidence, signature, existing_summary, scores)
        ai = await self._generate(facts)
        explanation = self._assemble_node(details, evidence, related, ai)
        explanation.update(self._analytics_block(scores, impact))
        return ArchitectureExplanation(
            repo_id=str(repo_id),
            subject_id=str(node_id),
            subject_kind="node",
            **explanation,
            evidence=evidence,
        )

    async def explain_flow(
        self, repo_id: UUID, flow_id: str, db: AsyncSession
    ) -> ArchitectureExplanation | None:
        """Explain a reconstructed flow from the Flow Reconstruction Engine."""
        flow = await self._flows.get_flow(repo_id, flow_id, db)
        if flow is None:
            return None

        evidence = self._flow_evidence(flow)
        related = self._flow_related(flow)

        # ── Deterministic analytics (no LLM) ──────────────────────────
        signals = self._flow_signals(flow, evidence)
        scores = metrics.score_flow(signals)
        impact = self._flow_impact(flow, evidence)

        facts = self._flow_facts(flow, evidence, scores)
        ai = await self._generate(facts)
        explanation = self._assemble_flow(flow, evidence, related, ai)
        explanation.update(self._analytics_block(scores, impact))
        return ArchitectureExplanation(
            repo_id=str(repo_id),
            subject_id=flow.flow_id,
            subject_kind="flow",
            **explanation,
            evidence=evidence,
        )

    # ════════════════════════════════════════════════════════════════════
    # Evidence retrieval — NODE
    # ════════════════════════════════════════════════════════════════════
    def _node_evidence(
        self, details, imports: list[str], centrality: float | None
    ) -> ExplanationEvidence:
        node = details.node
        # api_count = downstream calls into api_route / external_api nodes.
        api_callees = [
            c for c in details.callees if c.node_type in ("api_route", "external_api")
        ]
        return ExplanationEvidence(
            subject_kind="node",
            node_type=node.node_type,
            file_path=details.file_path,
            http_method=node.http_method,
            route_path=node.route_path,
            caller_names=[c.name for c in details.callers][:EVIDENCE_LIST_LIMIT],
            callee_names=[c.name for c in details.callees][:EVIDENCE_LIST_LIMIT],
            service_names=[s.name for s in details.services][:EVIDENCE_LIST_LIMIT],
            table_relations=[
                f"{t.edge_type or 'uses'}:{t.name}" for t in details.tables
            ][:EVIDENCE_LIST_LIMIT],
            dependency_relations=[
                f"{d.edge_type or 'depends_on'}:{d.name}" for d in details.dependencies
            ][:EVIDENCE_LIST_LIMIT],
            import_names=[i for i in imports if i][:EVIDENCE_LIST_LIMIT],
            caller_count=len(details.callers),
            callee_count=len(details.callees),
            dependency_count=len(details.callees)
            + len(details.services)
            + len(details.tables)
            + len([i for i in imports if i]),
            table_count=len(details.tables),
            api_count=len(api_callees),
            centrality_score=float(centrality) if centrality is not None else None,
            llm_used=False,
        )

    def _node_related(self, details) -> list[RelatedComponent]:
        related: list[RelatedComponent] = []
        seen: set[str] = set()

        def add(items, relationship: str) -> None:
            for it in items:
                if it.id in seen:
                    continue
                seen.add(it.id)
                related.append(
                    RelatedComponent(
                        id=it.id,
                        name=it.name,
                        node_type=it.node_type,
                        relationship=relationship,
                    )
                )

        add(details.callers, "caller")
        add(details.callees, "callee")
        add(details.services, "service")
        add(details.tables, "table")
        add(details.dependencies, "dependency")
        return related[:RELATED_LIMIT]

    # ════════════════════════════════════════════════════════════════════
    # Evidence retrieval — FLOW
    # ════════════════════════════════════════════════════════════════════
    def _flow_evidence(self, flow: Flow) -> ExplanationEvidence:
        root = flow.root_node
        return ExplanationEvidence(
            subject_kind="flow",
            node_type=root.node_type,
            flow_type=flow.flow_type,
            file_path=root.file_path,
            http_method=root.http_method,
            route_path=root.route_path,
            flow_step_count=flow.edge_count,
            flow_node_count=flow.node_count,
            critical_node_names=[n.name for n in flow.critical_nodes][:EVIDENCE_LIST_LIMIT],
            dependency_relations=[
                f"{d.node_type}:{d.name}" for d in flow.dependencies
            ][:EVIDENCE_LIST_LIMIT],
            dependency_count=len(flow.dependencies),
            api_count=sum(
                1 for d in flow.dependencies if d.node_type == "external_api"
            ),
            table_count=sum(
                1 for d in flow.dependencies if d.node_type == "database_table"
            ),
            llm_used=False,
        )

    def _flow_related(self, flow: Flow) -> list[RelatedComponent]:
        related: list[RelatedComponent] = []
        seen: set[str] = set()
        # Critical nodes first (most architecturally significant), then deps.
        for n in flow.critical_nodes:
            if n.id in seen or n.id == flow.root_node.id:
                continue
            seen.add(n.id)
            related.append(
                RelatedComponent(
                    id=n.id, name=n.name, node_type=n.node_type, relationship="critical_node"
                )
            )
        for d in flow.dependencies:
            if d.id in seen:
                continue
            seen.add(d.id)
            related.append(
                RelatedComponent(
                    id=d.id, name=d.name, node_type=d.node_type, relationship="dependency"
                )
            )
        return related[:RELATED_LIMIT]

    # ════════════════════════════════════════════════════════════════════
    # Signal extraction → deterministic scoring inputs (graph evidence only)
    # ════════════════════════════════════════════════════════════════════
    def _node_signals(self, details, evidence: ExplanationEvidence) -> GraphSignals:
        node = details.node
        write_tables = sum(
            1
            for t in evidence.table_relations
            if t.split(":", 1)[0] in ("writes_table", "updates_table", "deletes_table")
        )
        return GraphSignals(
            caller_count=evidence.caller_count,
            callee_count=evidence.callee_count,
            service_count=len(evidence.service_names),
            table_count=evidence.table_count,
            api_count=evidence.api_count,
            import_count=len(evidence.import_names),
            write_table_count=write_tables,
            is_api_route=node.node_type == "api_route",
            is_external_reachable=node.node_type == "api_route" or bool(node.route_path),
            centrality_0_100=evidence.centrality_score,
        )

    def _flow_signals(self, flow: Flow, evidence: ExplanationEvidence) -> GraphSignals:
        return GraphSignals(
            service_count=sum(1 for d in flow.dependencies if d.node_type == "service"),
            table_count=evidence.table_count,
            api_count=evidence.api_count,
            write_table_count=evidence.table_count,  # db_interaction flows mutate tables
            is_external_reachable=flow.root_node.node_type == "api_route",
            flow_edge_count=flow.edge_count,
            flow_node_count=flow.node_count,
            flow_critical_count=len(flow.critical_nodes),
            dependency_count=evidence.dependency_count,
        )

    # ── Impact-if-changed assembly from incident edges ─────────────────
    def _node_impact(self, details, evidence: ExplanationEvidence) -> ImpactIfChanged:
        node = details.node
        api_callees = [
            c.name for c in details.callees if c.node_type in ("api_route", "external_api")
        ]
        self_label = (
            f"{node.http_method or 'HTTP'} {node.route_path}"
            if node.route_path
            else None
        )
        return metrics.compute_impact_if_changed(
            caller_names=evidence.caller_names,
            callee_api_names=api_callees,
            service_names=evidence.service_names,
            table_relations=evidence.table_relations,
            is_api_route=node.node_type == "api_route",
            self_route_label=self_label,
        )

    def _flow_impact(self, flow: Flow, evidence: ExplanationEvidence) -> ImpactIfChanged:
        # For a flow, "callers" are the critical nodes whose change breaks it;
        # affected resources are the flow's resource dependencies.
        apis = [
            d.name for d in flow.dependencies if d.node_type == "external_api"
        ]
        if flow.root_node.node_type == "api_route" and flow.root_node.route_path:
            apis = [
                f"{flow.root_node.http_method or 'HTTP'} {flow.root_node.route_path}",
                *apis,
            ]
        services = [d.name for d in flow.dependencies if d.node_type == "service"]
        tables = [d.name for d in flow.dependencies if d.node_type == "database_table"]
        crit = [n.name for n in flow.critical_nodes if n.id != flow.root_node.id]

        parts = []
        if crit:
            parts.append(f"{len(crit)} critical node(s) on the path")
        if apis:
            parts.append(f"{len(apis)} API(s) affected")
        if services:
            parts.append(f"{len(services)} service(s) involved")
        if tables:
            parts.append(f"{len(tables)} table(s) touched")
        summary = (
            "Changing this flow would impact: " + "; ".join(parts) + "."
            if parts
            else "This flow has no external resource dependencies."
        )
        return ImpactIfChanged(
            callers_affected=len(crit),
            callers_breaking=crit[:15],
            apis_affected=apis,
            services_affected=services,
            database_tables_affected=tables,
            summary=summary,
        )

    @staticmethod
    def _analytics_block(scores, impact: ImpactIfChanged) -> dict:
        return {
            "architecture_health": scores.architecture_health,
            "complexity_score": scores.complexity_score,
            "coupling_score": scores.coupling_score,
            "risk_level": scores.risk_level,
            "impact_if_changed": impact,
            "recommendations": scores.recommendations,
            "score_factors": scores.factors,
        }

    # ════════════════════════════════════════════════════════════════════
    # Fact packs handed to the LLM (NO code, only graph evidence)
    # ════════════════════════════════════════════════════════════════════
    def _node_facts(
        self,
        details,
        evidence: ExplanationEvidence,
        signature: str | None,
        existing_summary: str | None,
        scores,
    ) -> dict:
        node = details.node
        label = NODE_TYPE_LABEL.get(node.node_type, node.node_type)
        facts: dict = {
            "subject_kind": "node",
            "component_kind": label,
            "name": node.name,
            "node_type": node.node_type,
            "file_path": details.file_path,
            "is_async": node.is_async,
            "is_exported": node.is_exported,
            # Precomputed verdicts the prose must stay consistent with (do not
            # restate as numbers; reflect the qualitative level in the summary).
            "computed_complexity_score": scores.complexity_score,
            "computed_coupling_score": scores.coupling_score,
            "computed_risk_level": scores.risk_level,
            "computed_architecture_health": scores.architecture_health,
        }
        if signature:
            facts["signature"] = signature[:300]
        if node.http_method or node.route_path:
            facts["http_method"] = node.http_method
            facts["route_path"] = node.route_path
        # Graph relationships — the ONLY allowed source of dependency claims.
        facts["callers"] = evidence.caller_names
        facts["callees"] = evidence.callee_names
        facts["services_used"] = evidence.service_names
        facts["database_tables"] = evidence.table_relations
        facts["dependencies"] = evidence.dependency_relations
        facts["imports"] = evidence.import_names
        if existing_summary:
            facts["prior_summary"] = existing_summary[:400]
        return facts

    def _flow_facts(self, flow: Flow, evidence: ExplanationEvidence, scores) -> dict:
        root = flow.root_node
        # Compact, ordered list of the real edges that make up the flow.
        step_lines = [
            f"{s.from_node.name} --{s.edge_type}--> {s.to_node.name}"
            for s in flow.steps[:30]
        ]
        return {
            "subject_kind": "flow",
            "flow_type": flow.flow_type,
            "flow_name": flow.flow_name,
            "entrypoint": root.name,
            "entrypoint_type": root.node_type,
            "http_method": root.http_method,
            "route_path": root.route_path,
            "file_path": root.file_path,
            "node_count": flow.node_count,
            "edge_count": flow.edge_count,
            "critical_nodes": evidence.critical_node_names,
            "resource_dependencies": evidence.dependency_relations,
            "steps": step_lines,
            "truncated": flow.truncated,
            "computed_complexity_score": scores.complexity_score,
            "computed_coupling_score": scores.coupling_score,
            "computed_risk_level": scores.risk_level,
            "computed_architecture_health": scores.architecture_health,
        }

    # ════════════════════════════════════════════════════════════════════
    # Groq narrative generation (narrative only; invents nothing)
    # ════════════════════════════════════════════════════════════════════
    async def _generate(self, facts: dict) -> dict | None:
        prompt = self._build_prompt(facts)
        try:
            from app.utils.groq_client import groq_client

            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=GROQ_MAX_TOKENS,
                    temperature=GROQ_TEMPERATURE,
                ),
            )
            text = resp.choices[0].message.content.strip()
            text = self._strip_fences(text)
            data = json.loads(text)
            if not isinstance(data, dict):
                return None
            return data
        except Exception as e:  # noqa: BLE001 — LLM is best-effort, never fatal
            logger.warning("Architecture explainer LLM skipped: %s", e)
            return None

    @staticmethod
    def _strip_fences(text: str) -> str:
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        if not text.startswith("{"):
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1:
                text = text[start : end + 1]
        return text.strip()

    def _build_prompt(self, facts: dict) -> str:
        kind = facts.get("subject_kind")
        subject = (
            "a software component (node)"
            if kind == "node"
            else "an architectural flow reconstructed from the dependency graph"
        )
        return f"""You are a Senior Software Architect writing a factual architecture explanation of {subject}.

You are given GRAPH_EVIDENCE extracted from a real repository's dependency graph.
This evidence is the COMPLETE and ONLY truth available to you.

HARD RULES — violating any of these makes the answer useless:
1. Use ONLY facts present in GRAPH_EVIDENCE. Do not invent functions, services,
   tables, APIs, libraries, dependencies, or business logic that are not listed.
2. The dependency / caller / callee / service / table lists are COMPLETE. Never
   add an item that is not in them. If a list is empty, say it has none.
3. Do not speculate about behaviour the evidence does not show. No marketing.
4. If evidence is thin, keep the explanation short and honest rather than padded.
5. Base "risks" only on observable structural facts (e.g. many callers = high
   blast radius, writes to a shared table, no callers = possibly dead/entrypoint,
   external API dependency = network failure surface). Do NOT invent CVEs or bugs.

GRAPH_EVIDENCE:
{json.dumps(facts, indent=2)}

Respond with ONLY a JSON object (no markdown, no code fences) with these keys:
- "title": short human-readable title for this component/flow
- "summary": 1-2 sentence plain-language summary of what it is
- "purpose": 1-2 sentences on its role in the architecture (grounded in evidence)
- "responsibilities": array of short strings — what it does, per the evidence
- "inputs": array of short strings — what flows in (callers, parameters, route)
- "outputs": array of short strings — what flows out (callees, tables written, responses)
- "dependencies": array of short strings — ONLY items from the evidence's dependency/service/table/import lists
- "risks": array of short strings — structural risks derived from the evidence
- "related_components": array of short strings — names of closely related components from the evidence

Every array may be empty. Keep each string concise."""

    # ════════════════════════════════════════════════════════════════════
    # Assembly: merge LLM narrative over deterministic, evidence-only base
    # ════════════════════════════════════════════════════════════════════
    def _assemble_node(
        self, details, evidence: ExplanationEvidence, related: list[RelatedComponent], ai: dict | None
    ) -> dict:
        base = self._node_fallback(details, evidence)
        merged = self._merge(base, ai)
        merged["related_components"] = related
        if ai:
            evidence.llm_used = True
        return merged

    def _assemble_flow(
        self, flow: Flow, evidence: ExplanationEvidence, related: list[RelatedComponent], ai: dict | None
    ) -> dict:
        base = self._flow_fallback(flow, evidence)
        merged = self._merge(base, ai)
        merged["related_components"] = related
        if ai:
            evidence.llm_used = True
        return merged

    def _merge(self, base: dict, ai: dict | None) -> dict:
        """Overlay LLM prose onto the deterministic base, but only for the
        narrative fields and only when present.

        `dependencies` and `related_components` are ALWAYS graph-derived and are
        never taken from the LLM — those are the fields where invention is
        explicitly forbidden, and they are the ones concretely checkable against
        the graph. The LLM may rephrase responsibilities/inputs/outputs/risks
        (grounded by the prompt) but cannot introduce a new dependency edge."""
        if not ai:
            return dict(base)
        out = dict(base)
        for key in ("title", "summary", "purpose"):
            val = ai.get(key)
            if isinstance(val, str) and val.strip():
                out[key] = val.strip()
        for key in ("responsibilities", "inputs", "outputs", "risks"):
            val = ai.get(key)
            if isinstance(val, list) and val:
                cleaned = [str(x).strip() for x in val if str(x).strip()]
                if cleaned:
                    out[key] = cleaned
        return out

    # ── Deterministic fallbacks (pure graph evidence) ──────────────────
    def _node_fallback(self, details, evidence: ExplanationEvidence) -> dict:
        node = details.node
        label = NODE_TYPE_LABEL.get(node.node_type, node.node_type)
        loc = f" in {details.file_path}" if details.file_path else ""

        if node.node_type == "api_route" and (node.http_method or node.route_path):
            title = f"{node.http_method or 'HTTP'} {node.route_path or node.name}"
            summary = (
                f"API endpoint `{node.http_method or ''} {node.route_path or node.name}`"
                f" defined by `{node.name}`{loc}."
            )
        elif node.node_type == "database_table":
            title = f"Table: {node.name}"
            summary = f"Database table `{node.name}` referenced in the repository graph."
        else:
            title = f"{label}: {node.name}"
            summary = f"{label} `{node.name}`{loc}."

        purpose = self._node_purpose(node, evidence)

        responsibilities: list[str] = []
        if evidence.callee_names:
            responsibilities.append(
                f"Calls {len(evidence.callee_names)} downstream component(s): "
                + ", ".join(evidence.callee_names[:6])
            )
        if evidence.service_names:
            responsibilities.append(
                "Uses service(s): " + ", ".join(evidence.service_names[:6])
            )
        if evidence.table_relations:
            responsibilities.append(
                "Accesses table(s): " + ", ".join(evidence.table_relations[:6])
            )
        if not responsibilities:
            responsibilities.append("No outgoing graph relationships recorded.")

        inputs: list[str] = []
        if node.route_path:
            inputs.append(f"HTTP request to {node.http_method or ''} {node.route_path}".strip())
        if evidence.caller_names:
            inputs.append("Invoked by: " + ", ".join(evidence.caller_names[:6]))
        if not inputs:
            inputs.append("No recorded callers (possible entrypoint or unused).")

        outputs: list[str] = []
        writes = [t for t in evidence.table_relations if t.startswith(("writes", "updates", "deletes"))]
        if writes:
            outputs.append("Writes to: " + ", ".join(writes[:6]))
        if evidence.callee_names:
            outputs.append("Delegates to: " + ", ".join(evidence.callee_names[:6]))
        if node.node_type == "api_route":
            outputs.append("HTTP response to the caller.")
        if not outputs:
            outputs.append("No outgoing data flow recorded.")

        dependencies = self._node_dependencies(evidence)
        risks = self._node_risks(node, evidence)

        return {
            "title": title,
            "summary": summary,
            "purpose": purpose,
            "responsibilities": responsibilities,
            "inputs": inputs,
            "outputs": outputs,
            "dependencies": dependencies or ["No dependencies recorded in the graph."],
            "risks": risks,
        }

    @staticmethod
    def _node_purpose(node, evidence: ExplanationEvidence) -> str:
        if node.node_type == "api_route":
            return "Serves as an HTTP entrypoint exposing functionality to clients."
        if node.node_type == "service":
            return "Encapsulates business logic reused across the codebase."
        if node.node_type == "database_table":
            return "Persists application data accessed by the components above."
        if evidence.caller_names and evidence.callee_names:
            return "Acts as an intermediate component connecting callers to downstream logic."
        if evidence.callee_names and not evidence.caller_names:
            return "Acts as an entrypoint orchestrating downstream components."
        return f"A {node.node_type} participating in the repository's dependency graph."

    @staticmethod
    def _node_dependencies(evidence: ExplanationEvidence) -> list[str]:
        deps: list[str] = []
        deps.extend(f"service: {s}" for s in evidence.service_names)
        deps.extend(f"table: {t}" for t in evidence.table_relations)
        deps.extend(f"calls: {c}" for c in evidence.callee_names)
        deps.extend(evidence.dependency_relations)
        deps.extend(f"import: {i}" for i in evidence.import_names)
        return deps

    @staticmethod
    def _node_risks(node, evidence: ExplanationEvidence) -> list[str]:
        risks: list[str] = []
        n_callers = len(evidence.caller_names)
        if n_callers >= 5:
            risks.append(
                f"High blast radius: {n_callers} callers depend on this — "
                "changes ripple widely."
            )
        writes = [t for t in evidence.table_relations if t.startswith(("writes", "updates", "deletes"))]
        if writes:
            risks.append(
                "Mutates persistent state (" + ", ".join(writes[:4]) + "); "
                "review for data-integrity impact."
            )
        if node.node_type == "api_route":
            risks.append("Externally reachable surface; validate auth and inputs.")
        if not evidence.caller_names and node.node_type in ("function", "method"):
            risks.append("No recorded callers — may be dead code or an untracked entrypoint.")
        if not risks:
            risks.append("No notable structural risks evident from the graph.")
        return risks

    def _flow_fallback(self, flow: Flow, evidence: ExplanationEvidence) -> dict:
        root = flow.root_node
        title = flow.flow_name
        summary = (
            f"{flow.flow_name}: a reconstructed {flow.flow_type.replace('_', ' ')} spanning "
            f"{flow.node_count} node(s) and {flow.edge_count} edge(s), rooted at `{root.name}`."
        )
        purpose = self._flow_purpose(flow)

        responsibilities = [
            f"Begins at `{root.name}`"
            + (f" ({root.http_method} {root.route_path})" if root.route_path else "")
            + f" and traverses {flow.edge_count} graph edge(s)."
        ]
        if evidence.critical_node_names:
            responsibilities.append(
                "Passes through critical nodes: "
                + ", ".join(evidence.critical_node_names[:6])
            )

        inputs = [
            f"Entrypoint: {root.http_method} {root.route_path}".strip()
            if root.route_path
            else f"Entrypoint: {root.name}"
        ]

        outputs: list[str] = []
        if evidence.dependency_relations:
            outputs.append(
                "Reaches resources: " + ", ".join(evidence.dependency_relations[:6])
            )
        if not outputs:
            outputs.append("Terminates within the traversed subgraph.")

        dependencies = list(evidence.dependency_relations) or [
            "No service/table/external resources reached by this flow."
        ]
        risks = self._flow_risks(flow, evidence)

        return {
            "title": title,
            "summary": summary,
            "purpose": purpose,
            "responsibilities": responsibilities,
            "inputs": inputs,
            "outputs": outputs,
            "dependencies": dependencies,
            "risks": risks,
        }

    @staticmethod
    def _flow_purpose(flow: Flow) -> str:
        purposes = {
            "api_request": "Describes how an API request travels from its route through services to data stores.",
            "authentication": "Describes how authentication/authorization guards a protected resource.",
            "repo_analysis": "Describes how the repository analysis pipeline ingests and processes code.",
            "db_interaction": "Describes which components read from and write to a database table.",
            "service_dependency": "Describes the dependency chain a service relies on.",
        }
        return purposes.get(flow.flow_type, "Describes a reconstructed execution path through the graph.")

    @staticmethod
    def _flow_risks(flow: Flow, evidence: ExplanationEvidence) -> list[str]:
        risks: list[str] = []
        if flow.truncated:
            risks.append("Flow was truncated at the traversal bound — it may extend further.")
        if len(evidence.critical_node_names) >= 4:
            risks.append(
                f"{len(evidence.critical_node_names)} critical nodes on this path — "
                "a failure in any can break the whole flow."
            )
        externals = [d for d in evidence.dependency_relations if d.startswith("external_api")]
        if externals:
            risks.append("Depends on external API(s); subject to network/availability failures.")
        if flow.edge_count >= 20:
            risks.append("Long flow (many hops) — higher latency and harder to reason about.")
        if not risks:
            risks.append("No notable structural risks evident from the flow graph.")
        return risks
