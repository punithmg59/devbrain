import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import {
  Gauge,
  Globe,
  Server,
  Database,
  Layers,
  PanelLeftOpen,
  PanelRightOpen,
  X,
  type LucideIcon,
} from "lucide-react";

import WorkspaceNav from "../components/architecture/WorkspaceNav";
import ArchitectureSidebar, {
  type ArchitectureCategory,
} from "../components/architecture/ArchitectureSidebar";
import ComponentList from "../components/architecture/ComponentList";
import SystemOverview from "../components/architecture/SystemOverview";
import ViewToggle, { type ArchView } from "../components/architecture/ViewToggle";

// Code-split React Flow + dagre: only loaded when the Graph view is opened.
const ArchitectureGraph = lazy(() => import("../components/architecture/ArchitectureGraph"));
import DetailsPanel from "../components/architecture/DetailsPanel";
import { useResizablePanel } from "../hooks/useResizablePanel";
import {
  architectureService,
  type ArchitectureComponents,
  type ArchitectureOverview,
  type ArchNodeSummary,
  type DependencyEdge,
  type NodeDetails,
} from "../services/architectureService";
import { flowService, type FlowSummary } from "../services/flowService";

const OVERVIEW_KEY = "overview";

interface CategoryMeta {
  key: string;
  label: string;
  icon: LucideIcon;
}

// "overview" is the System Overview stats view; the rest map to
// architecture/components group keys returned by the API.
const CATEGORY_META: CategoryMeta[] = [
  { key: OVERVIEW_KEY, label: "System Overview", icon: Gauge },
  { key: "system", label: "System Diagram", icon: Layers },
  { key: "api_request", label: "Request Flow Diagram", icon: Globe },
  { key: "service_dependency", label: "Service Dependency Diagram", icon: Server },
  { key: "db_interaction", label: "Database Relationship Diagram", icon: Database },
];

const COLLAPSED_WIDTH = 56;

export default function ArchitectureExplorerPage() {
  const { repoId = "" } = useParams<{ repoId: string }>();

  const [activeKey, setActiveKey] = useState<string>(OVERVIEW_KEY);
  const [activeSubKey, setActiveSubKey] = useState<string | null>(null);

  // Flows list
  const [flows, setFlows] = useState<FlowSummary[]>([]);

  // Health report
  const [health, setHealth] = useState<any>(null);

  // Components (counts + items) from the repository graph.
  const [components, setComponents] = useState<ArchitectureComponents | null>(null);
  const [componentsLoading, setComponentsLoading] = useState(true);
  const [componentsError, setComponentsError] = useState<string | null>(null);

  // System Overview aggregate metrics.
  const [overview, setOverview] = useState<ArchitectureOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  // List vs Graph view (per non-overview category).
  const [viewMode, setViewMode] = useState<ArchView>("list");

  // Dependency edges — lazily loaded the first time Graph view is opened.
  const [graphEdges, setGraphEdges] = useState<DependencyEdge[]>([]);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);
  const graphRequested = useRef(false);

  // Selected entity + its details.
  const [selectedNode, setSelectedNode] = useState<ArchNodeSummary | null>(null);
  const [details, setDetails] = useState<NodeDetails | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);
  const detailReq = useRef(0);

  // Left sidebar: resizable + collapsible.
  const sidebar = useResizablePanel({
    initial: 280,
    min: 220,
    max: 460,
    storageKey: "devbrain-arch-sidebar-width",
    edge: "right",
  });
  const [collapsed, setCollapsed] = useState(false);

  // Right details panel: resizable + closable.
  const right = useResizablePanel({
    initial: 360,
    min: 300,
    max: 600,
    storageKey: "devbrain-arch-details-width",
    edge: "left",
  });
  const [rightOpen, setRightOpen] = useState(true);

  // Mobile/tablet overlay drawers.
  const [mobileLeftOpen, setMobileLeftOpen] = useState(false);
  const [mobileRightOpen, setMobileRightOpen] = useState(false);

  // Click an entity → load its details into the right panel.
  const handleSelectNode = useCallback(
    async (node: ArchNodeSummary) => {
      const reqId = ++detailReq.current;
      setSelectedNode(node);
      setRightOpen(true);
      setMobileRightOpen(true); // no-op visually on lg+ (drawer is lg:hidden)
      setDetails(null);
      setDetailsLoading(true);
      setDetailsError(null);
      try {
        const d = await architectureService.getNode(repoId, node.id);
        if (reqId === detailReq.current) setDetails(d);
      } catch {
        if (reqId === detailReq.current) setDetailsError("Failed to load details.");
      } finally {
        if (reqId === detailReq.current) setDetailsLoading(false);
      }
    },
    [repoId]
  );

  useEffect(() => {
    if (!repoId) return;
    let alive = true;
    // Reset lazy graph state when the repo changes.
    graphRequested.current = false;
    setGraphEdges([]);
    setGraphError(null);
    setComponentsLoading(true);
    setComponentsError(null);
    architectureService
      .getComponents(repoId)
      .then((data) => {
        if (alive) setComponents(data);
      })
      .catch(() => {
        if (alive) setComponentsError("Failed to load architecture components");
      })
      .finally(() => {
        if (alive) setComponentsLoading(false);
      });

    setOverviewLoading(true);
    setOverviewError(null);
    architectureService
      .getOverview(repoId)
      .then((data) => {
        if (alive) setOverview(data);
      })
      .catch(() => {
        if (alive) setOverviewError("Failed to load system overview");
      })
      .finally(() => {
        if (alive) setOverviewLoading(false);
      });

    flowService
      .listFlows(repoId)
      .then((data) => {
        if (alive) setFlows(data.flows);
      })
      .catch(() => {
        console.error("Failed to load flows");
      });

    architectureService
      .getHealth(repoId)
      .then((data) => {
        if (alive) setHealth(data);
      })
      .catch(() => {
        console.error("Failed to load health report");
      });

    return () => {
      alive = false;
    };
  }, [repoId]);

  const countsByKey = useMemo(() => {
    const map: Record<string, number> = {
      system: components?.groups.reduce((acc, g) => acc + g.count, 0) ?? 0,
    };
    flows.forEach((f) => {
      map[f.flow_type] = (map[f.flow_type] || 0) + 1;
    });
    return map;
  }, [components, flows]);

  const categories: ArchitectureCategory[] = useMemo(
    () =>
      CATEGORY_META.map((c) => {
        let subItems = undefined;
        if (c.key === "api_request" || c.key === "service_dependency" || c.key === "db_interaction") {
          subItems = flows
            .filter((f) => f.flow_type === c.key)
            .map((f) => ({ id: f.flow_id, label: f.flow_name }));
        }

        return {
          key: c.key,
          label: c.label,
          icon: c.icon,
          count: c.key === OVERVIEW_KEY ? null : countsByKey[c.key] ?? 0,
          subItems,
        };
      }),
    [countsByKey, flows]
  );

  const activeLabel = CATEGORY_META.find((c) => c.key === activeKey)?.label ?? "";
  const activeItems = useMemo(() => {
    if (activeKey === "system" && components) {
      return components.groups
        .filter((g) => g.key === "apis" || g.key === "services" || g.key === "tables")
        .flatMap((g) => g.items);
    }
    return components?.groups.find((g) => g.key === activeKey)?.items ?? [];
  }, [components, activeKey]);

  // Index every component node (id → summary) for graph node metadata.
  const nodeIndex = useMemo(() => {
    const map = new Map<string, ArchNodeSummary>();
    components?.groups.forEach((g) => g.items.forEach((it) => map.set(it.id, it)));
    return map;
  }, [components]);

  const seedIds = useMemo(() => activeItems.map((i) => i.id), [activeItems]);

  // Flow Details (for Diagram Modes)
  const [activeFlow, setActiveFlow] = useState<any>(null);
  const [flowLoading, setFlowLoading] = useState(false);
  const [flowError, setFlowError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeSubKey || !repoId) {
      setActiveFlow(null);
      return;
    }
    let alive = true;
    setFlowLoading(true);
    setFlowError(null);
    flowService
      .getFlow(repoId, activeSubKey)
      .then((data) => {
        if (alive) setActiveFlow(data.flow);
      })
      .catch(() => {
        if (alive) setFlowError("Failed to load flow diagram");
      })
      .finally(() => {
        if (alive) setFlowLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [repoId, activeSubKey]);

  // Process query parameters for cross-navigation
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const nodeParam = params.get("node");
    const flowParam = params.get("flow");
    
    if (flowParam && flows.length > 0) {
      // Find which category this flow belongs to
      const flow = flows.find(f => f.flow_id === flowParam);
      if (flow) {
        setActiveKey(flow.flow_type);
        setActiveSubKey(flow.flow_id);
        // Clear param from URL without reloading
        params.delete("flow");
        const newUrl = window.location.pathname + (params.toString() ? `?${params.toString()}` : '');
        window.history.replaceState({}, '', newUrl);
      }
    } else if (nodeParam && components) {
      // Look for the node in components to select it and activate its category
      for (const group of components.groups) {
        const found = group.items.find(item => item.id === nodeParam);
        if (found) {
          setActiveKey(group.key);
          handleSelectNode(found);
          // Clear param from URL without reloading
          params.delete("node");
          const newUrl = window.location.pathname + (params.toString() ? `?${params.toString()}` : '');
          window.history.replaceState({}, '', newUrl);
          break;
        }
      }
    }
  }, [flows, components, handleSelectNode]);

  // Lazy-load dependency edges the first time the graph view is opened.
  useEffect(() => {
    if (viewMode !== "graph" || !repoId || graphRequested.current) return;
    graphRequested.current = true;
    setGraphLoading(true);
    setGraphError(null);
    architectureService
      .getDependencies(repoId)
      .then((d) => setGraphEdges(d.edges))
      .catch(() => setGraphError("Failed to load dependency edges"))
      .finally(() => setGraphLoading(false));
  }, [viewMode, repoId]);

  const isDiagramMode =
    activeKey === "system" ||
    activeKey === "api_request" ||
    activeKey === "service_dependency" ||
    activeKey === "db_interaction";

  const isFlowMode =
    activeKey === "api_request" ||
    activeKey === "service_dependency" ||
    activeKey === "db_interaction";

  // Compute effective graph props
  const effectiveGraphLoading = isFlowMode ? flowLoading : (componentsLoading || graphLoading);
  const effectiveGraphError = isFlowMode
    ? flowError || (activeSubKey && !activeFlow && !flowLoading ? "Flow not found" : null)
    : (componentsError ?? graphError);

  const effectiveSeedIds = useMemo(() => {
    if (!isFlowMode) return seedIds;
    if (activeFlow) {
      const ids = new Set<string>();
      if (activeFlow.root_node) ids.add(activeFlow.root_node.id);
      activeFlow.steps?.forEach((step: any) => {
        ids.add(step.from_node.id);
        ids.add(step.to_node.id);
      });
      return Array.from(ids);
    }
    return [];
  }, [isFlowMode, seedIds, activeFlow]);

  const effectiveNodeIndex = useMemo(() => {
    if (!isFlowMode) return nodeIndex;
    const map = new Map<string, ArchNodeSummary>();
    if (activeFlow) {
      const addRef = (ref: any) => {
        if (!map.has(ref.id)) {
          const orig = nodeIndex.get(ref.id);
          if (orig) {
            map.set(ref.id, orig);
          } else {
            map.set(ref.id, {
              id: ref.id,
              name: ref.name,
              node_type: ref.node_type,
              full_path: ref.file_path || "",
              file_path: ref.file_path || null,
              language: null,
              http_method: ref.http_method || null,
              route_path: ref.route_path || null,
              is_exported: false,
              is_async: false,
              start_line: null,
              end_line: null,
            });
          }
        }
      };
      if (activeFlow.root_node) addRef(activeFlow.root_node);
      activeFlow.steps?.forEach((step: any) => {
        addRef(step.from_node);
        addRef(step.to_node);
      });
    }
    return map;
  }, [isFlowMode, nodeIndex, activeFlow]);

  const effectiveEdges = useMemo(() => {
    if (!isFlowMode) return graphEdges;
    if (activeFlow) {
      return activeFlow.steps.map((step: any) => ({
        source: step.from_node.id,
        target: step.to_node.id,
        type: step.edge_type,
      }));
    }
    return [];
  }, [isFlowMode, graphEdges, activeFlow]);

  // Sidebar and detail states are defined at the top.

  // Persist collapse + open state.
  useEffect(() => {
    try {
      setCollapsed(window.localStorage.getItem("devbrain-arch-sidebar-collapsed") === "1");
      const ro = window.localStorage.getItem("devbrain-arch-details-open");
      if (ro !== null) setRightOpen(ro === "1");
    } catch {
      /* ignore */
    }
  }, []);
  useEffect(() => {
    try {
      window.localStorage.setItem("devbrain-arch-sidebar-collapsed", collapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [collapsed]);
  useEffect(() => {
    try {
      window.localStorage.setItem("devbrain-arch-details-open", rightOpen ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [rightOpen]);

  // Close drawers on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMobileLeftOpen(false);
        setMobileRightOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleSelectCategory = useCallback((key: string, subKey?: string) => {
    setActiveKey(key);
    setActiveSubKey(subKey ?? null);
    if (key !== OVERVIEW_KEY && viewMode !== "graph") {
      setViewMode("graph"); // Default to graph view for diagram modes
    }
    setMobileLeftOpen(false);
  }, [viewMode]);

  // handleSelectNode is defined at the top.

  const sidebarContent = (
    <ArchitectureSidebar
      items={categories}
      activeKey={activeKey}
      activeSubKey={activeSubKey}
      onSelect={handleSelectCategory}
      collapsed={collapsed}
      onToggleCollapse={() => setCollapsed(!collapsed)}
    />
  );

  const detailsProps = {
    selected: selectedNode,
    details,
    loading: detailsLoading,
    error: detailsError,
    health,
    onSelectRelated: handleSelectNode,
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#0a0a0c] text-white">
      <WorkspaceNav repoId={repoId} />

      <div className="relative flex min-h-0 flex-1">
        {/* ── Left sidebar (md+) ─────────────────────────────── */}
        <aside
          className="hidden shrink-0 border-r border-white/10 transition-[width] duration-200 ease-out md:block"
          style={{ width: collapsed ? COLLAPSED_WIDTH : sidebar.width }}
        >
          {sidebarContent}
        </aside>

        {/* Left resizer (only when expanded) */}
        {!collapsed && (
          <div
            role="separator"
            aria-orientation="vertical"
            onPointerDown={sidebar.onResizerPointerDown}
            className={`hidden w-1.5 shrink-0 cursor-col-resize select-none transition-colors hover:bg-purple-500/30 md:block ${
              sidebar.isDragging ? "bg-purple-500/40" : "bg-transparent"
            }`}
          />
        )}

        {/* ── Center: searchable component list ──────────────── */}
        <main className="relative min-w-0 flex-1">
          {/* Mobile: open components drawer */}
          <button
            type="button"
            onClick={() => setMobileLeftOpen(true)}
            className="absolute left-2 top-2 z-20 grid h-9 w-9 place-items-center rounded-lg border border-white/10 bg-[#0b0b0d]/80 text-gray-300 backdrop-blur transition-colors hover:text-white md:hidden"
            aria-label="Open components"
          >
            <PanelLeftOpen className="h-4 w-4" />
          </button>

          {/* Open details: drawer on small screens; reopen the inline panel on lg+. */}
          <button
            type="button"
            onClick={() => {
              setRightOpen(true);
              setMobileRightOpen(true);
            }}
            className={`absolute right-2 top-2 z-20 grid h-9 w-9 place-items-center rounded-lg border border-white/10 bg-[#0b0b0d]/80 text-gray-300 backdrop-blur transition-colors hover:text-white ${
              rightOpen ? "lg:hidden" : ""
            }`}
            aria-label="Open details"
          >
            <PanelRightOpen className="h-4 w-4" />
          </button>

          {activeKey === OVERVIEW_KEY ? (
            <SystemOverview
              overview={overview}
              loading={overviewLoading}
              error={overviewError}
            />
          ) : viewMode === "graph" ? (
            <Suspense
              fallback={
                <div className="flex h-full items-center justify-center bg-[#0a0a0c]">
                  <Loader2 className="h-6 w-6 animate-spin text-purple-400" />
                </div>
              }
            >
              <ArchitectureGraph
                label={activeLabel}
                seedIds={effectiveSeedIds}
                nodeIndex={effectiveNodeIndex}
                edges={effectiveEdges}
                health={health}
                loading={effectiveGraphLoading}
                error={effectiveGraphError}
                selectedId={selectedNode?.id ?? null}
                onSelectNode={handleSelectNode}
                headerRight={!isDiagramMode && <ViewToggle mode={viewMode} onChange={setViewMode} />}
              />
            </Suspense>
          ) : (
            <ComponentList
              label={activeLabel}
              items={activeItems}
              loading={componentsLoading}
              error={componentsError}
              selectedId={selectedNode?.id ?? null}
              onSelect={handleSelectNode}
              headerRight={<ViewToggle mode={viewMode} onChange={setViewMode} />}
            />
          )}
        </main>

        {/* Right resizer + panel (lg+) */}
        {rightOpen && (
          <>
            <div
              role="separator"
              aria-orientation="vertical"
              onPointerDown={right.onResizerPointerDown}
              className={`hidden w-1.5 shrink-0 cursor-col-resize select-none transition-colors hover:bg-purple-500/30 lg:block ${
                right.isDragging ? "bg-purple-500/40" : "bg-transparent"
              }`}
            />
            <aside
              className="hidden shrink-0 border-l border-white/10 lg:block"
              style={{ width: right.width }}
            >
              <DetailsPanel onClose={() => setRightOpen(false)} {...detailsProps} />
            </aside>
          </>
        )}

        {/* ── Mobile left drawer ─────────────────────────────── */}
        {mobileLeftOpen && (
          <div className="absolute inset-0 z-40 md:hidden">
            <div
              className="absolute inset-0 animate-fade-in bg-black/60 backdrop-blur-sm"
              onClick={() => setMobileLeftOpen(false)}
            />
            <div className="absolute left-0 top-0 h-full w-72 max-w-[80%] animate-slide-in-right border-r border-white/10 shadow-2xl">
              <ArchitectureSidebar
                items={categories}
                activeKey={activeKey}
                onSelect={handleSelectCategory}
                collapsed={false}
                onToggleCollapse={() => setMobileLeftOpen(false)}
              />
            </div>
          </div>
        )}

        {/* ── Tablet/mobile right drawer ─────────────────────── */}
        {mobileRightOpen && (
          <div className="absolute inset-0 z-40 lg:hidden">
            <div
              className="absolute inset-0 animate-fade-in bg-black/60 backdrop-blur-sm"
              onClick={() => setMobileRightOpen(false)}
            />
            <div className="absolute right-0 top-0 h-full w-96 max-w-[88%] animate-slide-in-right border-l border-white/10 shadow-2xl">
              <DetailsPanel onClose={() => setMobileRightOpen(false)} {...detailsProps} />
            </div>
          </div>
        )}
      </div>

      {/* a11y: drawers also close on Escape */}
      {(mobileLeftOpen || mobileRightOpen) && (
        <button
          type="button"
          onClick={() => {
            setMobileLeftOpen(false);
            setMobileRightOpen(false);
          }}
          className="sr-only"
        >
          <X className="h-4 w-4" /> Close drawer
        </button>
      )}
    </div>
  );
}
