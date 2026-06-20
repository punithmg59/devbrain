"""Response schemas for the Flow Reconstruction Engine.

Flows are COMPUTED from the existing repository graph (nodes / edges) by
deterministic graph traversal — no new tables, no AI, no LLM. Every step in a
flow is backed by a real edge, so output is reproducible and non-hallucinated.
"""

from pydantic import BaseModel


class FlowNodeRef(BaseModel):
    """A node that participates in a flow."""

    id: str
    name: str
    node_type: str
    file_path: str | None = None
    http_method: str | None = None
    route_path: str | None = None


class FlowStep(BaseModel):
    """One directed hop in a flow: `from_node` --edge_type--> `to_node`.

    `order` is the position of the step within the flow (0-based). `depth` is the
    traversal distance of `to_node` from the flow root.
    """

    order: int
    depth: int
    edge_type: str
    from_node: FlowNodeRef
    to_node: FlowNodeRef


class Flow(BaseModel):
    """A reconstructed architectural flow.

    `flow_id` is deterministic — `{flow_type}::{root_node_id}` — so it can be
    re-derived on demand by GET /flows/{flow_id} without persistence.
    """

    flow_id: str
    flow_name: str
    flow_type: str
    root_node: FlowNodeRef
    steps: list[FlowStep]
    critical_nodes: list[FlowNodeRef]
    dependencies: list[FlowNodeRef]
    node_count: int
    edge_count: int
    truncated: bool = False


class FlowSummary(BaseModel):
    """Lightweight flow descriptor for the list endpoint (no full step list)."""

    flow_id: str
    flow_name: str
    flow_type: str
    root_node: FlowNodeRef
    step_count: int
    critical_node_count: int


class FlowTypeCount(BaseModel):
    flow_type: str
    count: int


class FlowListResponse(BaseModel):
    repo_id: str
    total: int
    type_counts: list[FlowTypeCount]
    flows: list[FlowSummary]


class FlowDetailResponse(BaseModel):
    repo_id: str
    flow: Flow


class FlowsFromNodeResponse(BaseModel):
    repo_id: str
    node: FlowNodeRef
    total: int
    flows: list[Flow]
