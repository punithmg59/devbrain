import dagre from "dagre";
import { MarkerType, Position, type Edge, type Node } from "reactflow";
import type { ArchNodeSummary, DependencyEdge } from "../../services/architectureService";

// ── Caps: bound the initial render so large repos never lag ────────────
export const SEED_LIMIT = 80; // category nodes seeded into the graph
export const GRAPH_NODE_LIMIT = 150; // seeds + neighbours
export const GRAPH_EDGE_LIMIT = 350;

const NODE_W = 184;
const NODE_H = 52;

// Only these edge types are visualised (per spec, plus close cousins).
const ALLOWED_EDGE_TYPES = new Set([
  "calls",
  "api_calls",
  "imports",
  "reads_table",
  "writes_table",
  "updates_table",
  "deletes_table",
  "inherits",
  "uses_service",
]);

export function normalizeEdgeType(t: string): string {
  if (t === "api_calls") return "calls";
  if (t === "updates_table" || t === "deletes_table") return "writes_table";
  return t;
}

export const EDGE_COLORS: Record<string, string> = {
  calls: "#60a5fa", // blue
  imports: "#94a3b8", // slate
  reads_table: "#34d399", // emerald
  writes_table: "#fb7185", // rose
  inherits: "#c084fc", // purple
  uses_service: "#fbbf24", // amber
};

export interface ArchNodeData {
  label: string;
  nodeType: string;
  filePath: string | null;
  summary: ArchNodeSummary;
  // runtime highlight flags (mutated by the graph component)
  dim?: boolean;
  focus?: boolean;
  match?: boolean;
}

export interface BuiltGraph {
  nodes: Node<ArchNodeData>[];
  edges: Edge[];
  truncated: boolean;
  candidateCount: number;
}

function synthSummary(id: string, name: string): ArchNodeSummary {
  return {
    id,
    name,
    node_type: "unknown",
    full_path: "",
    file_path: null,
    language: null,
    http_method: null,
    route_path: null,
    is_exported: false,
    is_async: false,
    start_line: null,
    end_line: null,
  };
}

/** Build a bounded subgraph around the selected category's seed nodes. */
export function buildGraph(
  seedIds: string[],
  nodeIndex: Map<string, ArchNodeSummary>,
  allEdges: DependencyEdge[],
  direction: "LR" | "TB" = "LR"
): BuiltGraph {
  const allowed = allEdges.filter((e) => ALLOWED_EDGE_TYPES.has(e.edge_type));

  // name fallback for ids that aren't in the component index
  const nameById = new Map<string, string>();
  for (const e of allowed) {
    if (!nameById.has(e.from_node_id)) nameById.set(e.from_node_id, e.from_name);
    if (!nameById.has(e.to_node_id)) nameById.set(e.to_node_id, e.to_name);
  }

  const seedSet = new Set(seedIds.slice(0, SEED_LIMIT));
  const included = new Set<string>(seedSet);

  // One hop out from the seeds (callers, callees, tables, services…).
  for (const e of allowed) {
    if (included.size >= GRAPH_NODE_LIMIT) break;
    const touches = seedSet.has(e.from_node_id) || seedSet.has(e.to_node_id);
    if (!touches) continue;
    if (included.size < GRAPH_NODE_LIMIT) included.add(e.from_node_id);
    if (included.size < GRAPH_NODE_LIMIT) included.add(e.to_node_id);
  }

  // Edges fully inside the included set.
  const seen = new Set<string>();
  const subEdges: DependencyEdge[] = [];
  for (const e of allowed) {
    if (subEdges.length >= GRAPH_EDGE_LIMIT) break;
    if (e.from_node_id === e.to_node_id) continue;
    if (!included.has(e.from_node_id) || !included.has(e.to_node_id)) continue;
    const norm = normalizeEdgeType(e.edge_type);
    const key = `${e.from_node_id}__${e.to_node_id}__${norm}`;
    if (seen.has(key)) continue;
    seen.add(key);
    subEdges.push(e);
  }

  const nodes: Node<ArchNodeData>[] = [...included].map((id) => {
    const summary = nodeIndex.get(id) ?? synthSummary(id, nameById.get(id) ?? id.slice(0, 8));
    return {
      id,
      type: "arch",
      position: { x: 0, y: 0 },
      data: {
        label: summary.name,
        nodeType: summary.node_type,
        filePath: summary.file_path,
        summary,
      },
    };
  });

  const edges: Edge[] = subEdges.map((e) => {
    const norm = normalizeEdgeType(e.edge_type);
    const color = EDGE_COLORS[norm] ?? "#64748b";
    return {
      id: `${e.from_node_id}__${e.to_node_id}__${norm}`,
      source: e.from_node_id,
      target: e.to_node_id,
      data: { kind: norm },
      style: { stroke: color, strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color, width: 16, height: 16 },
    };
  });

  layout(nodes, edges, direction);

  return {
    nodes,
    edges,
    truncated: seedIds.length > seedSet.size || subEdges.length >= GRAPH_EDGE_LIMIT,
    candidateCount: seedIds.length,
  };
}

function layout(nodes: Node<ArchNodeData>[], edges: Edge[], direction: "LR" | "TB") {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, nodesep: 36, ranksep: 90, marginx: 24, marginy: 24 });
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);

  const horizontal = direction === "LR";
  nodes.forEach((n) => {
    const pos = g.node(n.id);
    n.position = { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 };
    n.sourcePosition = horizontal ? Position.Right : Position.Bottom;
    n.targetPosition = horizontal ? Position.Left : Position.Top;
  });
}
