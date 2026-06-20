"""Deterministic architecture analytics — graph evidence in, scores out.

Every value produced here is computed in pure Python from graph facts that the
explainer already retrieved (callers, callees, dependency count, table / API
interactions, and — when available — precomputed graph centrality from
`impact_metrics`). The LLM is never involved in scoring: no number, health
verdict, risk level, or impact figure originates from a model. This keeps the
analytics reproducible and free of hallucinated architecture.

Outputs:
  * complexity_score    1–10   structural complexity (fan-in/out, deps, breadth)
  * coupling_score      1–10   how entangled the component is with the rest
  * risk_level          Low / Medium / High
  * architecture_health Healthy / Moderate Risk / High Risk
  * impact_if_changed   concrete blast radius from incident edges
  * recommendations     rule-derived remediation hints
  * score_factors       audit trail: each input that moved a score
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.architecture import ImpactIfChanged, MetricFactor

# ── Calibration thresholds ────────────────────────────────────────────
# Chosen so a small leaf function scores ~1–2 and a god-object hub scores ~9–10.
# These are normalization anchors, NOT guesses about behaviour: a node with
# >= COUPLING_FANOUT_MAX outgoing relations saturates the coupling axis.
COUPLING_FANIN_MAX = 12      # callers at which fan-in coupling saturates
COUPLING_FANOUT_MAX = 12     # callees+services+tables at which fan-out saturates
COMPLEXITY_DEP_MAX = 15      # total distinct dependencies at which deps saturate
COMPLEXITY_BREADTH_MAX = 6   # distinct relation *kinds* (callers/callees/svc/tbl/api/import)

HEALTH_HEALTHY = "Healthy"
HEALTH_MODERATE = "Moderate Risk"
HEALTH_HIGH = "High Risk"

RISK_LOW = "Low"
RISK_MEDIUM = "Medium"
RISK_HIGH = "High"


@dataclass
class GraphSignals:
    """Normalized inputs — all sourced from real graph edges / metrics."""

    caller_count: int = 0
    callee_count: int = 0
    service_count: int = 0
    table_count: int = 0
    api_count: int = 0          # outgoing api_calls / external_api relations
    import_count: int = 0
    write_table_count: int = 0  # subset of table interactions that mutate state
    is_api_route: bool = False
    is_external_reachable: bool = False
    centrality_0_100: float | None = None  # precomputed, if available

    # Flow-specific (only set for flow subjects)
    flow_edge_count: int = 0
    flow_node_count: int = 0
    flow_critical_count: int = 0

    @property
    def dependency_count(self) -> int:
        # Distinct outgoing structural dependencies.
        return self.callee_count + self.service_count + self.table_count + self.import_count

    @property
    def fan_out(self) -> int:
        return self.callee_count + self.service_count + self.table_count + self.api_count

    @property
    def fan_in(self) -> int:
        return self.caller_count


@dataclass
class ScoreResult:
    complexity_score: int
    coupling_score: int
    risk_level: str
    architecture_health: str
    recommendations: list[str]
    factors: list[MetricFactor] = field(default_factory=list)


def _clamp_1_10(x: float) -> int:
    return int(max(1, min(10, round(x))))


def _norm(value: int, ceiling: int) -> float:
    return min(1.0, value / ceiling) if ceiling > 0 else 0.0


# ════════════════════════════════════════════════════════════════════════
# Complexity: how much is going on structurally inside/around this component.
# ════════════════════════════════════════════════════════════════════════
def compute_complexity(sig: GraphSignals) -> tuple[int, list[MetricFactor]]:
    factors: list[MetricFactor] = []

    dep_norm = _norm(sig.dependency_count, COMPLEXITY_DEP_MAX)
    # Breadth = how many distinct *kinds* of relation it participates in.
    kinds = sum(
        1
        for c in (
            sig.caller_count,
            sig.callee_count,
            sig.service_count,
            sig.table_count,
            sig.api_count,
            sig.import_count,
        )
        if c > 0
    )
    breadth_norm = _norm(kinds, COMPLEXITY_BREADTH_MAX)
    fanout_norm = _norm(sig.fan_out, COUPLING_FANOUT_MAX)

    raw = dep_norm * 0.45 + fanout_norm * 0.35 + breadth_norm * 0.20
    score = _clamp_1_10(1 + raw * 9)

    factors.append(MetricFactor(label="dependencies", value=float(sig.dependency_count),
                                detail=f"{sig.dependency_count} distinct outgoing dependencies"))
    factors.append(MetricFactor(label="fan_out", value=float(sig.fan_out),
                                detail=f"{sig.fan_out} downstream calls/services/tables/APIs"))
    factors.append(MetricFactor(label="relation_breadth", value=float(kinds),
                                detail=f"{kinds} distinct kinds of graph relationship"))
    return score, factors


# ════════════════════════════════════════════════════════════════════════
# Coupling: how entangled with the rest of the system (fan-in + fan-out + centrality).
# ════════════════════════════════════════════════════════════════════════
def compute_coupling(sig: GraphSignals) -> tuple[int, list[MetricFactor]]:
    factors: list[MetricFactor] = []

    fanin_norm = _norm(sig.fan_in, COUPLING_FANIN_MAX)
    fanout_norm = _norm(sig.fan_out, COUPLING_FANOUT_MAX)
    cohesion_penalty = fanin_norm * 0.5 + fanout_norm * 0.5

    # Centrality (graph importance) reinforces coupling when precomputed.
    if sig.centrality_0_100 is not None:
        cent_norm = sig.centrality_0_100 / 100.0
        raw = cohesion_penalty * 0.65 + cent_norm * 0.35
        factors.append(MetricFactor(label="centrality", value=round(sig.centrality_0_100, 2),
                                    detail="precomputed graph centrality (0–100)"))
    else:
        raw = cohesion_penalty

    score = _clamp_1_10(1 + raw * 9)
    factors.append(MetricFactor(label="fan_in", value=float(sig.fan_in),
                                detail=f"{sig.fan_in} callers depend on this"))
    factors.append(MetricFactor(label="fan_out", value=float(sig.fan_out),
                                detail=f"{sig.fan_out} outgoing dependencies"))
    return score, factors


# ════════════════════════════════════════════════════════════════════════
# Risk + health: combine complexity, coupling, blast-radius and state mutation.
# ════════════════════════════════════════════════════════════════════════
def compute_risk_and_health(
    sig: GraphSignals, complexity: int, coupling: int
) -> tuple[str, str, list[MetricFactor]]:
    factors: list[MetricFactor] = []

    # Weighted structural risk on a 0–10 scale.
    risk_raw = complexity * 0.35 + coupling * 0.45
    # Amplifiers grounded in concrete facts.
    if sig.write_table_count > 0:
        risk_raw += 1.0
        factors.append(MetricFactor(label="mutates_state", value=float(sig.write_table_count),
                                    detail=f"writes to {sig.write_table_count} table(s)"))
    if sig.is_external_reachable:
        risk_raw += 0.8
        factors.append(MetricFactor(label="external_surface", value=1.0,
                                    detail="externally reachable API surface"))
    if sig.fan_in >= COUPLING_FANIN_MAX:
        risk_raw += 0.8
        factors.append(MetricFactor(label="high_blast_radius", value=float(sig.fan_in),
                                    detail=f"{sig.fan_in} callers — wide blast radius"))

    risk_raw = max(0.0, min(10.0, risk_raw))
    if risk_raw >= 6.5:
        risk = RISK_HIGH
    elif risk_raw >= 3.5:
        risk = RISK_MEDIUM
    else:
        risk = RISK_LOW

    # Health is the human-facing rollup of the same signal.
    if risk == RISK_HIGH:
        health = HEALTH_HIGH
    elif risk == RISK_MEDIUM:
        health = HEALTH_MODERATE
    else:
        health = HEALTH_HEALTHY

    factors.append(MetricFactor(label="risk_index", value=round(risk_raw, 2),
                                detail="weighted complexity+coupling+amplifiers (0–10)"))
    return risk, health, factors


# ════════════════════════════════════════════════════════════════════════
# Recommendations: rule-derived remediation, each tied to a concrete signal.
# ════════════════════════════════════════════════════════════════════════
def compute_recommendations(
    sig: GraphSignals, complexity: int, coupling: int, risk: str
) -> list[str]:
    recs: list[str] = []

    if sig.fan_out >= COUPLING_FANOUT_MAX:
        recs.append(
            f"Split responsibilities: {sig.fan_out} outgoing dependencies suggest this "
            "component does too much — consider extracting cohesive sub-units."
        )
    if sig.dependency_count >= COMPLEXITY_DEP_MAX:
        recs.append(
            "Reduce dependencies: high dependency count increases change cost — "
            "consolidate or remove unused collaborators."
        )
    if sig.fan_in >= COUPLING_FANIN_MAX:
        recs.append(
            f"Add an abstraction: {sig.fan_in} callers depend directly on this — "
            "introduce an interface/facade to decouple them from internals."
        )
    if sig.service_count >= 3 and sig.table_count >= 3:
        recs.append(
            "Improve cohesion: this touches many services and tables at once — "
            "group related data access behind dedicated repositories."
        )
    if sig.write_table_count >= 2:
        recs.append(
            "Isolate writes: multiple table mutations here — centralize persistence "
            "to protect data integrity and ease testing."
        )
    if coupling >= 8 and not recs:
        recs.append(
            "Reduce coupling: high entanglement with the rest of the system — "
            "introduce boundaries to localize change."
        )
    if not recs:
        if risk == RISK_LOW:
            recs.append("No structural action needed — metrics are within healthy bounds.")
        else:
            recs.append("Monitor: metrics are elevated but no single threshold is breached.")
    return recs


# ════════════════════════════════════════════════════════════════════════
# Impact-if-changed: concrete blast radius straight from incident edges.
# ════════════════════════════════════════════════════════════════════════
def compute_impact_if_changed(
    *,
    caller_names: list[str],
    callee_api_names: list[str],
    service_names: list[str],
    table_relations: list[str],
    is_api_route: bool,
    self_route_label: str | None,
) -> ImpactIfChanged:
    callers_breaking = caller_names[:15]
    apis_affected = list(callee_api_names)
    # If the subject is itself an API, changing it breaks that API contract.
    if is_api_route and self_route_label:
        apis_affected = [self_route_label, *apis_affected]
    services_affected = list(service_names)
    tables_affected = [t.split(":", 1)[-1] for t in table_relations]

    parts: list[str] = []
    if caller_names:
        parts.append(f"{len(caller_names)} caller(s) would need review")
    if apis_affected:
        parts.append(f"{len(apis_affected)} API contract(s) affected")
    if services_affected:
        parts.append(f"{len(services_affected)} service(s) involved")
    if tables_affected:
        parts.append(f"{len(tables_affected)} table(s) touched")
    summary = (
        "Changing this would: " + "; ".join(parts) + "."
        if parts
        else "No downstream callers, APIs, services, or tables are affected by this change."
    )

    return ImpactIfChanged(
        callers_affected=len(caller_names),
        callers_breaking=callers_breaking,
        apis_affected=apis_affected,
        services_affected=services_affected,
        database_tables_affected=tables_affected,
        summary=summary,
    )


def score_node(sig: GraphSignals) -> ScoreResult:
    complexity, cf = compute_complexity(sig)
    coupling, kf = compute_coupling(sig)
    risk, health, rf = compute_risk_and_health(sig, complexity, coupling)
    recs = compute_recommendations(sig, complexity, coupling, risk)
    return ScoreResult(
        complexity_score=complexity,
        coupling_score=coupling,
        risk_level=risk,
        architecture_health=health,
        recommendations=recs,
        factors=[*cf, *kf, *rf],
    )


# ── Flow scoring: a flow's complexity/coupling come from its span ──────
def score_flow(sig: GraphSignals) -> ScoreResult:
    factors: list[MetricFactor] = []

    edge_norm = _norm(sig.flow_edge_count, 25)
    node_norm = _norm(sig.flow_node_count, 25)
    crit_norm = _norm(sig.flow_critical_count, 8)

    complexity = _clamp_1_10(1 + (edge_norm * 0.5 + node_norm * 0.3 + crit_norm * 0.2) * 9)
    # A flow's coupling is driven by how many critical nodes + resources it spans.
    coupling = _clamp_1_10(1 + (crit_norm * 0.5 + _norm(sig.dependency_count, 10) * 0.5) * 9)

    factors.append(MetricFactor(label="flow_edges", value=float(sig.flow_edge_count),
                                detail=f"{sig.flow_edge_count} edges traversed"))
    factors.append(MetricFactor(label="flow_nodes", value=float(sig.flow_node_count),
                                detail=f"{sig.flow_node_count} nodes spanned"))
    factors.append(MetricFactor(label="critical_nodes", value=float(sig.flow_critical_count),
                                detail=f"{sig.flow_critical_count} critical nodes on the path"))

    risk, health, rf = compute_risk_and_health(sig, complexity, coupling)
    recs: list[str] = []
    if sig.flow_critical_count >= 4:
        recs.append(
            f"Add resilience: {sig.flow_critical_count} critical nodes on this path — "
            "a failure in any breaks the flow; consider redundancy or circuit breakers."
        )
    if sig.flow_edge_count >= 20:
        recs.append(
            "Shorten the path: long flow increases latency and failure surface — "
            "look for hops that can be collapsed."
        )
    if sig.api_count > 0:
        recs.append("Guard external calls: add timeouts/retries on outbound dependencies.")
    if not recs:
        recs.append("Flow is within healthy structural bounds — no action needed.")

    return ScoreResult(
        complexity_score=complexity,
        coupling_score=coupling,
        risk_level=risk,
        architecture_health=health,
        recommendations=recs,
        factors=[*factors, *rf],
    )
