import { useCallback, useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Node,
  type NodeMouseHandler,
} from "reactflow";
import "reactflow/dist/style.css";
import { Search, Loader2, AlertCircle, Network, Maximize2 } from "lucide-react";

import ArchGraphNode from "./ArchGraphNode";
import {
  buildGraph,
  EDGE_COLORS,
  SEED_LIMIT,
  type ArchNodeData,
} from "./graphLayout";
import type {
  ArchNodeSummary,
  DependencyEdge,
} from "../../services/architectureService";

const nodeTypes = { arch: ArchGraphNode };

interface ArchitectureGraphProps {
  label: string;
  seedIds: string[];
  nodeIndex: Map<string, ArchNodeSummary>;
  edges: DependencyEdge[];
  health?: any;
  loading: boolean;
  error: string | null;
  selectedId: string | null;
  onSelectNode: (node: ArchNodeSummary) => void;
  headerRight?: React.ReactNode;
}

function minimapColor(n: Node<ArchNodeData>): string {
  const t = n.data.nodeType;
  if (t === "api_route") return "#22c55e";
  if (t === "class") return "#a855f7";
  if (t === "service") return "#f59e0b";
  if (t === "database_table") return "#f43f5e";
  if (t === "method") return "#14b8a6";
  if (t === "function") return "#3b82f6";
  return "#64748b";
}

function Flow({
  seedIds,
  nodeIndex,
  edges,
  health,
  selectedId,
  onSelectNode,
}: Pick<ArchitectureGraphProps, "seedIds" | "nodeIndex" | "edges" | "health" | "selectedId" | "onSelectNode">) {
  const rf = useReactFlow();
  const [query, setQuery] = useState("");

  const built = useMemo(
    () => buildGraph(seedIds, nodeIndex, edges),
    [seedIds, nodeIndex, edges]
  );

  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<ArchNodeData>([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState([]);

  // Adjacency for highlight (direct deps / callers / tables).
  const neighbors = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const e of built.edges) {
      if (!m.has(e.source)) m.set(e.source, new Set());
      if (!m.has(e.target)) m.set(e.target, new Set());
      m.get(e.source)!.add(e.target);
      m.get(e.target)!.add(e.source);
    }
    return m;
  }, [built]);

  // Reset graph whenever the source data changes.
  useEffect(() => {
    setRfNodes(built.nodes);
    setRfEdges(built.edges);
  }, [built, setRfNodes, setRfEdges]);

  // Apply selection + search highlight + health highlights.
  useEffect(() => {
    const q = query.trim().toLowerCase();
    
    // Create a map of hotspots for quick lookup
    const hotspotMap = new Map<string, any>();
    if (health?.hotspots) {
      health.hotspots.forEach((hs: any) => {
        hotspotMap.set(hs.node_id, hs);
      });
    }

    setRfNodes((ns) =>
      ns.map((n) => {
        const isMatch = q.length > 0 && n.data.label.toLowerCase().includes(q);
        let focus = false;
        let dim = false;
        if (selectedId) {
          focus = n.id === selectedId || (neighbors.get(selectedId)?.has(n.id) ?? false);
          dim = !focus;
        }
        if (q) dim = !isMatch;

        const hotspot = hotspotMap.get(n.id);
        const healthRisk = hotspot ? hotspot.score : undefined;

        return { ...n, data: { ...n.data, focus, dim, match: isMatch, healthRisk } };
      })
    );
    setRfEdges((es) =>
      es.map((e) => {
        let visible = true;
        if (selectedId) visible = e.source === selectedId || e.target === selectedId;
        return {
          ...e,
          animated: selectedId ? visible : false,
          style: { ...e.style, opacity: selectedId && !visible ? 0.1 : 1 },
        };
      })
    );
  }, [selectedId, query, neighbors, health, setRfNodes, setRfEdges]);

  const onNodeClick = useCallback<NodeMouseHandler>(
    (_, node) => {
      const data = node.data as ArchNodeData;
      onSelectNode(data.summary);
    },
    [onSelectNode]
  );

  const fitMatches = useCallback(() => {
    const q = query.trim().toLowerCase();
    const matchNodes = rfNodes.filter((n) => q && n.data.label.toLowerCase().includes(q));
    if (matchNodes.length) {
      rf.fitView({ nodes: matchNodes.map((n) => ({ id: n.id })), duration: 400, padding: 0.4 });
    }
  }, [query, rfNodes, rf]);

  return (
    <div className="relative h-full w-full">
      {/* Search */}
      <div className="absolute left-3 top-3 z-10 flex items-center gap-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fitMatches()}
            placeholder="Search nodes…"
            className="w-52 rounded-lg border border-white/10 bg-[#0b0b0d]/90 py-1.5 pl-8 pr-2 text-xs text-white placeholder:text-gray-600 outline-none backdrop-blur focus:border-purple-500/50"
          />
        </div>
        <button
          type="button"
          onClick={() => rf.fitView({ duration: 400, padding: 0.2 })}
          title="Fit view"
          className="grid h-8 w-8 place-items-center rounded-lg border border-white/10 bg-[#0b0b0d]/90 text-gray-300 backdrop-blur transition-colors hover:text-white"
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </button>
      </div>

      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        maxZoom={2}
        nodesConnectable={false}
        elementsSelectable
        onlyRenderVisibleElements
        proOptions={{ hideAttribution: false }}
        className="bg-[#0a0a0c]"
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#ffffff14" />
        <Controls className="!border-white/10 !bg-[#0b0b0d] [&_button]:!border-white/10 [&_button]:!bg-[#15151a] [&_button]:!fill-gray-300" />
        <MiniMap
          pannable
          zoomable
          nodeColor={minimapColor}
          maskColor="rgba(0,0,0,0.6)"
          className="!bg-[#0b0b0d]"
          style={{ border: "1px solid rgba(255,255,255,0.1)" }}
        />
      </ReactFlow>
    </div>
  );
}

export default function ArchitectureGraph({
  label,
  seedIds,
  nodeIndex,
  edges,
  loading,
  error,
  selectedId,
  onSelectNode,
  headerRight,
}: ArchitectureGraphProps) {
  const truncated = seedIds.length > SEED_LIMIT;

  return (
    <div className="flex h-full flex-col bg-[#0a0a0c]">
      {/* Header */}
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-white/10 px-4">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4 text-purple-400" />
          <span className="text-sm font-medium text-white">{label}</span>
          <span className="rounded-md bg-white/5 px-2 py-0.5 text-[11px] text-gray-400">Graph</span>
          {truncated && (
            <span className="rounded-md bg-amber-500/10 px-2 py-0.5 text-[11px] text-amber-400">
              showing first {SEED_LIMIT} of {seedIds.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Legend />
          {headerRight}
        </div>
      </div>

      {/* Body */}
      <div className="relative min-h-0 flex-1">
        {loading ? (
          <Centered icon={<Loader2 className="h-6 w-6 animate-spin text-purple-400" />} title="Building graph…" />
        ) : error ? (
          <Centered icon={<AlertCircle className="h-6 w-6 text-red-400" />} title="Couldn’t load graph" sub={error} />
        ) : seedIds.length === 0 ? (
          <Centered icon={<Network className="h-6 w-6 text-gray-500" />} title="Nothing to visualize" sub={`No ${label.toLowerCase()} in this repository.`} />
        ) : (
          <ReactFlowProvider>
            <Flow
              seedIds={seedIds}
              nodeIndex={nodeIndex}
              edges={edges}
              selectedId={selectedId}
              onSelectNode={onSelectNode}
            />
          </ReactFlowProvider>
        )}
      </div>
    </div>
  );
}

function Legend() {
  const items: [string, string][] = [
    ["calls", EDGE_COLORS.calls],
    ["imports", EDGE_COLORS.imports],
    ["reads_table", EDGE_COLORS.reads_table],
    ["writes_table", EDGE_COLORS.writes_table],
    ["inherits", EDGE_COLORS.inherits],
    ["uses_service", EDGE_COLORS.uses_service],
  ];
  return (
    <div className="hidden items-center gap-2.5 xl:flex">
      {items.map(([label, color]) => (
        <span key={label} className="flex items-center gap-1 text-[10px] text-gray-500">
          <span className="h-0.5 w-3 rounded" style={{ background: color }} />
          {label}
        </span>
      ))}
    </div>
  );
}

function Centered({ icon, title, sub }: { icon: React.ReactNode; title: string; sub?: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center p-6 text-center">
      <div className="mb-3 grid h-12 w-12 place-items-center rounded-xl border border-white/10 bg-white/5">
        {icon}
      </div>
      <h3 className="text-sm font-semibold text-gray-300">{title}</h3>
      {sub && <p className="mt-1 max-w-xs text-xs text-gray-500">{sub}</p>}
    </div>
  );
}
