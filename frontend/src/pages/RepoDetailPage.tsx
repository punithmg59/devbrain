import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Code2,
  File,
  FileCode2,
  Folder,
  FolderOpen,
  Globe,
  Layers,
  LayoutList,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
  Zap,
} from "lucide-react";

import {
  getApiRoutes,
  getFileTree,
  getNodes,
  getRepoDetail,
  getRepoStats,
  summarizeAll,
  summarizeNode,
} from "../services/repoDetailService";
import { repoService } from "../services/repoService";
import type {
  FileTreeNode,
  NodeResponse,
  RepoStats,
  ApiRoutes,
  PaginatedNodes,
} from "../types/repo";

import FileDetailPanel from "../components/FileDetailPanel";
import NodeDetailPanel from "../components/NodeDetailPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";

// ── Extension color map ─────────────────────────────────────────

function extColor(ext: string | null | undefined): string {
  if (!ext) return "text-gray-500";
  const e = ext.replace(".", "");
  if (["ts", "tsx"].includes(e)) return "text-blue-400";
  if (["py"].includes(e)) return "text-green-400";
  if (["js", "jsx"].includes(e)) return "text-yellow-400";
  if (["css", "scss", "sass"].includes(e)) return "text-pink-400";
  if (["json"].includes(e)) return "text-orange-400";
  if (["md", "mdx"].includes(e)) return "text-gray-400";
  return "text-gray-500";
}

// ── File tree item ──────────────────────────────────────────────

const FileTreeItem = ({
  node,
  expanded,
  onToggle,
  onSelectFile,
  selectedFileId,
  searchFilter,
  collapsed,
}: {
  node: FileTreeNode;
  expanded: Set<string>;
  onToggle: (path: string) => void;
  onSelectFile: (id: string) => void;
  selectedFileId: string | null;
  searchFilter: string;
  collapsed?: boolean;
}) => {
  const isExpanded = expanded.has(node.path);
  const isSelected = node.type === "file" && node.id === selectedFileId;
  const passesFilter =
    !searchFilter ||
    node.name.toLowerCase().includes(searchFilter.toLowerCase());

  // For folders, also check if any descendant passes
  const hasMatchingDescendant = useMemo(() => {
    if (!searchFilter) return true;
    if (node.type === "file") return passesFilter;
    const check = (n: FileTreeNode): boolean => {
      if (n.name.toLowerCase().includes(searchFilter.toLowerCase())) return true;
      return n.children.some(check);
    };
    return check(node);
  }, [node, searchFilter, passesFilter]);

  if (!hasMatchingDescendant) return null;

  const indent = node.depth * 16;

  if (node.type === "folder") {
    return (
      <>
        <button
          onClick={() => onToggle(node.path)}
          className="w-full flex items-center gap-1.5 py-1 px-2 text-left hover:bg-gray-800/50 rounded transition-colors group"
          style={{ paddingLeft: `${indent + 8}px` }}
          title={node.name}
        >
          {isExpanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-gray-600 shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-gray-600 shrink-0" />
          )}
          {isExpanded ? (
            <FolderOpen className="w-4 h-4 text-yellow-500/70 shrink-0" />
          ) : (
            <Folder className="w-4 h-4 text-yellow-500/50 shrink-0" />
          )}
          <span className={`text-sm text-gray-300 truncate ${collapsed ? "sr-only" : ""}`}>{node.name}</span>
          {node.file_count != null && (
            <span className={`ml-auto text-[10px] text-gray-600 shrink-0 ${collapsed ? "sr-only" : ""}`}>
              {node.file_count}
            </span>
          )}
        </button>
        {isExpanded &&
          node.children.map((child) => (
            <FileTreeItem
              key={child.id}
              node={child}
              expanded={expanded}
              onToggle={onToggle}
              onSelectFile={onSelectFile}
              selectedFileId={selectedFileId}
              searchFilter={searchFilter}
            />
          ))}
      </>
    );
  }

  // File
  return (
    <button
      onClick={() => onSelectFile(node.id)}
      className={`w-full flex items-center gap-1.5 py-1 px-2 text-left rounded transition-colors ${
        isSelected
          ? "bg-purple-900/30 border border-purple-700/30"
          : "hover:bg-gray-800/50 border border-transparent"
      }`}
      style={{ paddingLeft: `${indent + 24}px` }}
      title={node.name}
    >
      <FileCode2 className={`w-3.5 h-3.5 shrink-0 ${extColor(node.extension)}`} />
      <span className={`text-sm text-gray-300 truncate ${collapsed ? "sr-only" : ""}`}>{node.name}</span>
      {node.line_count != null && (
        <span className="ml-auto text-[10px] text-gray-600 shrink-0">
          {node.line_count}
        </span>
      )}
    </button>
  );
};

// Memoize FileTreeItem to avoid re-renders during resize
const MemoFileTreeItem = (React.memo(FileTreeItem) as unknown) as typeof FileTreeItem;

// ── NodeCard ────────────────────────────────────────────────────

const NodeCard = ({
  node,
  repoId,
  onUpdate,
  onClick,
}: {
  node: NodeResponse;
  repoId: string;
  onUpdate: (id: string, summary: string, tags: string[]) => void;
  onClick: () => void;
}) => {
  const [summarizing, setSummarizing] = useState(false);

  const handleSummarize = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setSummarizing(true);
    try {
      const res = await summarizeNode(repoId, node.id);
      onUpdate(node.id, res.summary, res.tags);
    } catch {
      /* silent */
    } finally {
      setSummarizing(false);
    }
  };

  const typeBadge: Record<string, string> = {
    function: "bg-blue-900/40 text-blue-400 border-blue-700/40",
    class: "bg-purple-900/40 text-purple-400 border-purple-700/40",
    method: "bg-teal-900/40 text-teal-400 border-teal-700/40",
    api_route: "bg-green-900/40 text-green-400 border-green-700/40",
  };

  return (
    <div
      onClick={onClick}
      className="p-3 bg-gray-900/50 border border-gray-800 rounded-lg hover:border-gray-700 cursor-pointer transition-colors"
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm text-gray-200">{node.name}</span>
          <span
            className={`px-1.5 py-0.5 text-[10px] font-medium rounded border ${
              typeBadge[node.node_type] ?? "bg-gray-800 text-gray-400 border-gray-700"
            }`}
          >
            {node.node_type}
          </span>
          {node.is_async && (
            <span className="px-1.5 py-0.5 text-[10px] bg-yellow-900/30 text-yellow-400 border border-yellow-700/30 rounded">
              async
            </span>
          )}
          {node.is_exported && (
            <span className="px-1.5 py-0.5 text-[10px] bg-emerald-900/30 text-emerald-400 border border-emerald-700/30 rounded">
              exported
            </span>
          )}
        </div>
        <div className="text-[10px] text-gray-500 bg-gray-800/50 px-2 py-0.5 rounded">
          Complexity: {node.complexity_score?.toFixed(1) ?? "0.0"}
        </div>
      </div>
      <p className="text-[11px] text-gray-600 font-mono truncate">{node.full_path}</p>
      {node.start_line != null && node.end_line != null && (
        <p className="text-[11px] text-gray-600 mt-0.5">
          Lines {node.start_line} – {node.end_line}
        </p>
      )}
      {node.signature && (
        <div className="mt-2 p-2 bg-[#0b0b0b] rounded border border-gray-800 text-[10px] text-gray-400 font-mono overflow-x-auto whitespace-pre">
          {node.signature}
        </div>
      )}
      {node.summary ? (
        <div className="mt-2">
          <p className="text-xs text-gray-400 italic">{node.summary}</p>
          {node.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {node.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 text-[10px] bg-gray-800 text-gray-400 rounded"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : (
        <button
          onClick={handleSummarize}
          disabled={summarizing}
          className="mt-2 flex items-center gap-1 text-[11px] px-2 py-1 bg-purple-600/20 text-purple-400 border border-purple-700/30 rounded hover:bg-purple-600/30 disabled:opacity-50 transition-colors"
        >
          {summarizing ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Sparkles className="w-3 h-3" />
          )}
          Summarize
        </button>
      )}
    </div>
  );
};

// ── Bar chart ───────────────────────────────────────────────────

function BarChart({
  data,
  colorFn,
}: {
  data: Record<string, number>;
  colorFn?: (key: string) => string;
}) {
  const entries = Object.entries(data).sort(([, a], [, b]) => b - a);
  const max = Math.max(...entries.map(([, v]) => v), 1);

  return (
    <div className="space-y-2">
      {entries.map(([key, value]) => (
        <div key={key} className="flex items-center gap-3">
          <span className="text-xs text-gray-400 w-24 text-right truncate shrink-0">
            {key || "unknown"}
          </span>
          <div className="flex-1 bg-gray-800/50 rounded-full h-5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                colorFn?.(key) ?? "bg-purple-600/60"
              }`}
              style={{ width: `${Math.max((value / max) * 100, 2)}%` }}
            />
          </div>
          <span className="text-xs text-gray-500 w-10 shrink-0">{value}</span>
        </div>
      ))}
    </div>
  );
}

// ── HTTP method badge ───────────────────────────────────────────

function HttpBadge({ method }: { method: string | null }) {
  const m = (method ?? "GET").toUpperCase();
  const colors: Record<string, string> = {
    GET: "bg-green-900/40 text-green-400 border-green-700/40",
    POST: "bg-blue-900/40 text-blue-400 border-blue-700/40",
    PUT: "bg-yellow-900/40 text-yellow-400 border-yellow-700/40",
    PATCH: "bg-orange-900/40 text-orange-400 border-orange-700/40",
    DELETE: "bg-red-900/40 text-red-400 border-red-700/40",
  };
  return (
    <span
      className={`px-2 py-0.5 text-xs font-mono font-bold rounded border ${
        colors[m] ?? "bg-gray-800 text-gray-400 border-gray-700"
      }`}
    >
      {m}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════
// Main Page
// ═══════════════════════════════════════════════════════════════

type Tab = "overview" | "functions" | "routes" | "stats";

export default function RepoDetailPage() {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [treeSearch, setTreeSearch] = useState("");
  const [summarizingAll, setSummarizingAll] = useState(false);

  // ── Functions tab state ──────────────────────────────────────
  const [funcSearch, setFuncSearch] = useState("");
  const [funcFilter, setFuncFilter] = useState<string | null>(null);
  const [funcPage, setFuncPage] = useState(1);
  const [allNodes, setAllNodes] = useState<NodeResponse[]>([]);
  const [nodesTotal, setNodesTotal] = useState(0);
  const [nodesHasMore, setNodesHasMore] = useState(false);
  const [nodesLoading, setNodesLoading] = useState(false);
  const [fallbackWarning, setFallbackWarning] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // ── Queries ──────────────────────────────────────────────────

  const {
    data: repo,
    isLoading: repoLoading,
    error: repoError,
    refetch: refetchRepo,
  } = useQuery({
    queryKey: ["repo-detail", repoId],
    queryFn: () => getRepoDetail(repoId!),
    enabled: !!repoId,
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: tree,
    isLoading: treeLoading,
    error: treeError,
  } = useQuery({
    queryKey: ["file-tree", repoId],
    queryFn: () => getFileTree(repoId!),
    enabled: !!repoId && repo?.analysis_status === "completed",
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: stats,
    isLoading: statsLoading,
  } = useQuery<RepoStats>({
    queryKey: ["repo-stats", repoId],
    queryFn: () => getRepoStats(repoId!),
    enabled: !!repoId && activeTab === "stats" && repo?.analysis_status === "completed",
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: apiRoutesData,
    isLoading: routesLoading,
  } = useQuery<ApiRoutes>({
    queryKey: ["api-routes", repoId],
    queryFn: () => getApiRoutes(repoId!),
    enabled: !!repoId && activeTab === "routes" && repo?.analysis_status === "completed",
    staleTime: 5 * 60 * 1000,
  });

  // ── Load nodes for Functions tab ─────────────────────────────

  const loadNodes = useCallback(
    async (search: string, filter: string | null, page: number, append: boolean) => {
      if (!repoId) return;
      setNodesLoading(true);
      try {
        const params: Record<string, string | number> = { page, limit: 50 };
        if (search) params.search = search;
        if (filter) params.node_type = filter;
        let res: PaginatedNodes = await getNodes(repoId, params);
        
        if (res.nodes.length === 0 && filter !== null) {
          setFallbackWarning(true);
          delete params.node_type;
          res = await getNodes(repoId, params);
          setFuncFilter(null);
        } else {
          setFallbackWarning(false);
        }

        setAllNodes((prev) => (append ? [...prev, ...res.nodes] : res.nodes));
        setNodesTotal(res.total);
        setNodesHasMore(res.has_more);
      } catch {
        // silent
      } finally {
        setNodesLoading(false);
      }
    },
    [repoId]
  );

  // Initial + filter change
  useEffect(() => {
    if (activeTab !== "functions" || !repoId || repo?.analysis_status !== "completed") return;
    setFuncPage(1);
    loadNodes(funcSearch, funcFilter, 1, false);
  }, [activeTab, repoId, funcFilter, repo?.analysis_status]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced search
  useEffect(() => {
    if (activeTab !== "functions") return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setFuncPage(1);
      loadNodes(funcSearch, funcFilter, 1, false);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [funcSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleLoadMore = () => {
    const next = funcPage + 1;
    setFuncPage(next);
    loadNodes(funcSearch, funcFilter, next, true);
  };

  const updateNodeSummary = (id: string, summary: string, tags: string[]) => {
    setAllNodes((prev) => prev.map((n) => (n.id === id ? { ...n, summary, tags } : n)));
  };

  // ── Handlers ─────────────────────────────────────────────────

  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const handleReanalyze = async () => {
    if (!repoId) return;
    try {
      await repoService.analyze(repoId);
      refetchRepo();
    } catch {
      // silent
    }
  };

  const handleSummarizeAll = async () => {
    if (!repoId) return;
    setSummarizingAll(true);
    try {
      await summarizeAll(repoId);
    } catch {
      // silent
    } finally {
      setSummarizingAll(false);
    }
  };

  // ── Render guards ────────────────────────────────────────────

  if (!repoId) return null;

  if (repoLoading) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <LoadingSpinner size="large" text="Loading repository..." />
      </div>
    );
  }

  if (repoError) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <ErrorState
          message={(repoError as Error).message}
          retry={() => refetchRepo()}
        />
      </div>
    );
  }

  if (!repo) return null;

  const isAnalysisIncomplete = repo.analysis_status !== "completed";
  // Sidebar sizing / collapse / drawer state
  const MIN_SIDEBAR = 260;
  const MAX_SIDEBAR = 700;
  const DEFAULT_SIDEBAR = 320;
  const COLLAPSED_WIDTH = 64;

  const [sidebarWidth, setSidebarWidth] = useState<number>(DEFAULT_SIDEBAR);
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true); // used as drawer open on mobile
  const [isDragging, setIsDragging] = useState(false);

  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const asideRef = useRef<HTMLDivElement | null>(null);
  const startXRef = useRef<number>(0);
  const startWidthRef = useRef<number>(DEFAULT_SIDEBAR);
  const rafRef = useRef<number | null>(null);

  // Load persisted settings
  useEffect(() => {
    try {
      const w = window.localStorage.getItem("devbrain-sidebar-width");
      const c = window.localStorage.getItem("devbrain-sidebar-collapsed");
      if (w) setSidebarWidth(Math.min(MAX_SIDEBAR, Math.max(MIN_SIDEBAR, Number(w))));
      if (c) setCollapsed(c === "1");
    } catch {
      // ignore
    }
  }, []);

  // Persist width and collapsed
  useEffect(() => {
    try {
      window.localStorage.setItem("devbrain-sidebar-width", String(sidebarWidth));
    } catch {}
  }, [sidebarWidth]);

  useEffect(() => {
    try {
      window.localStorage.setItem("devbrain-sidebar-collapsed", collapsed ? "1" : "0");
    } catch {}
  }, [collapsed]);

  // Pointer handlers for resizer
  const onResizerPointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    (e.target as Element).setPointerCapture(e.pointerId);
    startXRef.current = e.clientX;
    startWidthRef.current = sidebarWidth;
    setIsDragging(true);

    const onPointerMove = (ev: PointerEvent) => {
      const dx = ev.clientX - startXRef.current;
      const newWidth = Math.min(MAX_SIDEBAR, Math.max(MIN_SIDEBAR, startWidthRef.current + dx));
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => setSidebarWidth(newWidth));
    };

    const onPointerUp = (ev: PointerEvent) => {
      setIsDragging(false);
      try {
        (e.target as Element).releasePointerCapture(e.pointerId);
      } catch {}
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  }, [sidebarWidth]);

  // Collapse / expand
  const toggleCollapse = useCallback(() => {
    setCollapsed((c) => {
      const next = !c;
      if (!next) {
        // expanding: ensure width within limits
        setSidebarWidth((w) => Math.min(MAX_SIDEBAR, Math.max(MIN_SIDEBAR, w || DEFAULT_SIDEBAR)));
      }
      return next;
    });
  }, []);

  // Keyboard shortcuts Alt+[ collapse, Alt+] expand
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (!ev.altKey) return;
      if (ev.key === "[") {
        setCollapsed(true);
      } else if (ev.key === "]") {
        setCollapsed(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // ── Tabs config ──────────────────────────────────────────────

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "overview", label: "Overview", icon: <Layers className="w-4 h-4" /> },
    { key: "functions", label: "Functions", icon: <Code2 className="w-4 h-4" /> },
    { key: "routes", label: "API Routes", icon: <Globe className="w-4 h-4" /> },
    { key: "stats", label: "Stats", icon: <LayoutList className="w-4 h-4" /> },
  ];

  // Grouped API routes
  const groupedRoutes = useMemo(() => {
    if (!apiRoutesData) return {};
    const groups: Record<string, NodeResponse[]> = {};
    for (const route of apiRoutesData.routes) {
      const m = (route.http_method ?? "GET").toUpperCase();
      if (!groups[m]) groups[m] = [];
      groups[m].push(route);
    }
    return groups;
  }, [apiRoutesData]);

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white flex">
      {/* ── Left panel: File tree sidebar ───────────────────── */}
      {/* Sidebar */}
      <aside
        ref={asideRef}
        className={`relative border-r border-gray-800 flex flex-col h-screen sticky top-0 bg-[#0b0b0b] ${isMobile ? "fixed z-30 left-0 top-0" : ""}`}
        style={{
          width: collapsed ? `${COLLAPSED_WIDTH}px` : `${sidebarWidth}px`,
          transition: isDragging ? "none" : "width .18s ease",
          transform: isMobile ? (sidebarOpen ? "translateX(0)" : "translateX(-110%)") : undefined,
        }}
        aria-expanded={!collapsed}
      >
        {/* Collapse button near header */}
        <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
          <button
            onClick={() => navigate("/dashboard")}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
            aria-label="Back to dashboard"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h2 className="text-sm font-semibold text-gray-200 truncate flex-1">{repo.full_name}</h2>
          <button
            onClick={toggleCollapse}
            className="w-8 h-8 bg-gray-900 border border-gray-800 rounded-full flex items-center justify-center text-gray-300 hover:bg-gray-800 transition-transform"
            aria-pressed={collapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <ChevronRight className={`w-4 h-4 transform ${collapsed ? "rotate-180" : ""}`} />
          </button>
        </div>

        {/* Search */}
        <div className="px-3 py-2 border-b border-gray-800">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-600" />
            <input
              type="text"
              placeholder="Filter files..."
              value={treeSearch}
              onChange={(e) => setTreeSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-gray-900 border border-gray-800 rounded text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-purple-700/50"
            />
          </div>
        </div>

        {/* Tree content (memoized) */}
        <div className="flex-1 overflow-y-auto px-1 py-1">
          {isAnalysisIncomplete ? (
            <div className="p-4 text-center">
              <Loader2 className="w-6 h-6 animate-spin text-purple-500 mx-auto mb-2" />
              <p className="text-xs text-gray-500">Analysis in progress...</p>
            </div>
          ) : treeLoading ? (
            <LoadingSpinner size="small" />
          ) : treeError ? (
            <p className="text-xs text-red-400 p-3">{(treeError as Error).message}</p>
          ) : tree && tree.length > 0 ? (
            tree.map((node) => (
              <MemoFileTreeItem
                key={node.id}
                node={node}
                expanded={expandedFolders}
                onToggle={toggleFolder}
                onSelectFile={setSelectedFileId}
                selectedFileId={selectedFileId}
                searchFilter={treeSearch}
                collapsed={collapsed}
              />
            ))
          ) : (
            <p className="text-xs text-gray-600 p-3">No files found</p>
          )}
        </div>

      </aside>

      {/* Resizer handle (only show on non-mobile) */}
      {!isMobile && (
        <div
          role="separator"
          tabIndex={0}
          onPointerDown={onResizerPointerDown}
          onKeyDown={(e) => {
            if (e.key === "ArrowLeft") setSidebarWidth((w) => Math.max(MIN_SIDEBAR, w - 20));
            if (e.key === "ArrowRight") setSidebarWidth((w) => Math.min(MAX_SIDEBAR, w + 20));
            if (e.key === "Escape") setIsDragging(false);
          }}
          className={`w-2 cursor-col-resize select-none bg-transparent hover:bg-purple-600/20 active:bg-purple-600/30 transition-colors ${isDragging ? "bg-purple-600/40" : ""}`}
          style={{
            height: "100vh",
          }}
          aria-orientation="vertical"
          aria-label="Resize sidebar"
        />
      )}
      {/* Mobile overlay (drawer) */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-20"
          onClick={() => setSidebarOpen(false)}
          aria-hidden
        />
      )}

      {/* ── Right panel: Main content ───────────────────────── */}
      <main className="flex-1 min-w-0 h-screen overflow-y-auto">
        {/* Tabs */}
        <div className="sticky top-0 z-10 bg-[#0f0f0f] border-b border-gray-800">
          <div className="flex items-center">
            {isMobile && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-3 mr-2 text-gray-300 hover:text-gray-100"
                aria-label="Open sidebar"
              >
                <LayoutList className="w-5 h-5" />
              </button>
            )}
            <div className="flex">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? "border-purple-500 text-purple-400"
                    : "border-transparent text-gray-500 hover:text-gray-300"
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="p-6 max-w-5xl">
          {/* ── Tab: Overview ─────────────────────────────────── */}
          {activeTab === "overview" && (
            <div>
              {/* Header */}
              <div className="flex items-start justify-between gap-4 mb-6">
                <div>
                  <h1 className="text-2xl font-bold">{repo.full_name}</h1>
                  <div className="flex items-center gap-2 mt-2">
                    {repo.language && (
                      <span className="px-2 py-0.5 text-xs bg-blue-900/30 text-blue-400 border border-blue-700/30 rounded">
                        {repo.language}
                      </span>
                    )}
                    <span
                      className={`px-2 py-0.5 text-xs rounded border ${
                        repo.analysis_status === "completed"
                          ? "bg-green-900/30 text-green-400 border-green-700/30"
                          : "bg-yellow-900/30 text-yellow-400 border-yellow-700/30"
                      }`}
                    >
                      {repo.analysis_status}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 flex-wrap">
                  {repo.analysis_status === "completed" && (
                    <>
                      <Link
                        to={`/repos/${repoId}/project-brain`}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gradient-to-r from-purple-600/20 to-blue-600/20 text-blue-400 border border-blue-700/30 hover:bg-blue-900/30 rounded-lg transition-colors"
                      >
                        <Zap className="w-3.5 h-3.5" />
                        Project Brain
                      </Link>
                      <Link
                        to={`/repos/${repoId}/impact`}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-purple-600 text-purple-400 hover:bg-purple-900/30 rounded-lg transition-colors"
                      >
                        <Zap className="w-3.5 h-3.5" />
                        Impact Radar
                      </Link>
                    </>
                  )}
                  <button
                    onClick={handleReanalyze}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Re-analyze
                  </button>
                  <button
                    onClick={handleSummarizeAll}
                    disabled={summarizingAll}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-purple-600/20 text-purple-400 border border-purple-700/30 rounded-lg hover:bg-purple-600/30 disabled:opacity-50 transition-colors"
                  >
                    {summarizingAll ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5" />
                    )}
                    Summarize All
                  </button>
                </div>
              </div>

              {/* Stats cards */}
              <div className="grid grid-cols-4 gap-4 mb-8">
                {[
                  {
                    label: "Total Files",
                    value: repo.total_files,
                    icon: <File className="w-5 h-5 text-blue-400" />,
                  },
                  {
                    label: "Total Functions",
                    value: repo.total_functions,
                    icon: <Code2 className="w-5 h-5 text-purple-400" />,
                  },
                  {
                    label: "Total Lines",
                    value: repo.total_lines,
                    icon: <LayoutList className="w-5 h-5 text-green-400" />,
                  },
                  {
                    label: "API Routes",
                    value: stats?.total_api_routes ?? 0,
                    icon: <Globe className="w-5 h-5 text-orange-400" />,
                  },
                ].map((card) => (
                  <div
                    key={card.label}
                    className="p-4 bg-gray-900/50 border border-gray-800 rounded-xl"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-gray-800/50 rounded-lg">{card.icon}</div>
                      <div>
                        <p className="text-2xl font-bold">
                          {card.value.toLocaleString()}
                        </p>
                        <p className="text-xs text-gray-500">{card.label}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Selected file detail or placeholder */}
              {selectedFileId ? (
                <FileDetailPanel
                  repoId={repoId}
                  fileId={selectedFileId}
                  onClose={() => setSelectedFileId(null)}
                />
              ) : (
                <EmptyState
                  icon={<Folder className="w-12 h-12" />}
                  title="Select a file from the sidebar"
                  description="Click on a file in the tree to explore its contents and functions"
                />
              )}
            </div>
          )}

          {/* ── Tab: Functions ─────────────────────────────────── */}
          {activeTab === "functions" && (
            <div>
              {/* Search */}
              <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600" />
                <input
                  type="text"
                  placeholder="Search functions..."
                  value={funcSearch}
                  onChange={(e) => setFuncSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-purple-700/50"
                />
              </div>

              {/* Filter pills */}
              <div className="flex flex-wrap gap-2 mb-5">
                {[
                  { key: null, label: "All" },
                  { key: "function", label: "Functions" },
                  { key: "class", label: "Classes" },
                  { key: "method", label: "Methods" },
                ].map((pill) => (
                  <button
                    key={pill.key ?? "all"}
                    onClick={() => setFuncFilter(pill.key)}
                    className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${
                      funcFilter === pill.key
                        ? "bg-purple-600/20 text-purple-400 border-purple-700/30"
                        : "bg-gray-900 text-gray-500 border-gray-800 hover:border-gray-700"
                    }`}
                  >
                    {pill.label}
                  </button>
                ))}
              </div>

              {/* Fallback warning */}
              {fallbackWarning && (
                <div className="mb-4 p-3 bg-yellow-900/30 border border-yellow-700/50 rounded-lg text-sm text-yellow-500">
                  No results found for the selected filter. Showing all nodes instead.
                </div>
              )}

              {/* Results */}
              {nodesLoading && allNodes.length === 0 ? (
                <LoadingSpinner text="Loading functions..." />
              ) : allNodes.length === 0 ? (
                <EmptyState title="No functions found" description="Try adjusting your search or filters" />
              ) : (
                <>
                  <p className="text-xs text-gray-600 mb-3">{nodesTotal} results</p>
                  <div className="space-y-6">
                    {Object.entries(
                      allNodes.reduce((acc, node) => {
                        const path = node.full_path ? node.full_path.split(':')[0] : "unknown";
                        if (!acc[path]) acc[path] = [];
                        acc[path].push(node);
                        return acc;
                      }, {} as Record<string, NodeResponse[]>)
                    ).map(([path, nodesInFile]) => (
                      <div key={path} className="space-y-2">
                        <h3 className="text-sm font-semibold text-gray-400 mb-2 border-b border-gray-800 pb-1 truncate">
                          {path}
                        </h3>
                        {nodesInFile.map((node) => (
                          <NodeCard
                            key={node.id}
                            node={node}
                            repoId={repoId}
                            onUpdate={updateNodeSummary}
                            onClick={() => setSelectedNodeId(node.id)}
                          />
                        ))}
                      </div>
                    ))}
                  </div>
                  {nodesHasMore && (
                    <button
                      onClick={handleLoadMore}
                      disabled={nodesLoading}
                      className="mt-4 w-full py-2.5 text-sm text-gray-400 bg-gray-900 border border-gray-800 rounded-lg hover:border-gray-700 disabled:opacity-50 transition-colors"
                    >
                      {nodesLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                      ) : (
                        "Load More"
                      )}
                    </button>
                  )}
                </>
              )}
            </div>
          )}

          {/* ── Tab: API Routes ───────────────────────────────── */}
          {activeTab === "routes" && (
            <div>
              {routesLoading ? (
                <LoadingSpinner text="Loading API routes..." />
              ) : !apiRoutesData || apiRoutesData.total === 0 ? (
                <EmptyState title="No API routes found" description="This repository may not contain any API endpoints" />
              ) : (
                <div className="space-y-6">
                  {Object.entries(groupedRoutes).map(([method, routes]) => (
                    <div key={method}>
                      <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
                        <HttpBadge method={method} />
                        <span>{routes.length} routes</span>
                      </h3>
                      <div className="space-y-2">
                        {routes.map((route) => (
                          <div
                            key={route.id}
                            onClick={() => setSelectedNodeId(route.id)}
                            className="p-3 bg-gray-900/50 border border-gray-800 rounded-lg hover:border-gray-700 cursor-pointer transition-colors"
                          >
                            <div className="flex items-center gap-3 mb-1">
                              <HttpBadge method={route.http_method} />
                              <span className="font-mono text-sm text-gray-200">
                                {route.route_path ?? route.full_path}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500">{route.name}</p>
                            <p className="text-[11px] text-gray-600 font-mono truncate">
                              {route.full_path}
                            </p>
                            {route.summary && (
                              <p className="text-xs text-gray-400 italic mt-1">{route.summary}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── Tab: Stats ────────────────────────────────────── */}
          {activeTab === "stats" && (
            <div>
              {statsLoading ? (
                <LoadingSpinner text="Loading statistics..." />
              ) : !stats ? (
                <EmptyState title="No stats available" />
              ) : (
                <div className="space-y-8">
                  {/* Node types */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-300 mb-3">
                      Node Types
                    </h3>
                    <BarChart
                      data={stats.node_types}
                      colorFn={(k) => {
                        const m: Record<string, string> = {
                          function: "bg-blue-600/60",
                          class: "bg-purple-600/60",
                          method: "bg-teal-600/60",
                          api_route: "bg-green-600/60",
                        };
                        return m[k] ?? "bg-gray-600/60";
                      }}
                    />
                  </div>

                  {/* Extensions */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-300 mb-3">
                      File Extensions
                    </h3>
                    <BarChart data={stats.extensions} />
                  </div>

                  {/* Languages */}
                  {Object.keys(stats.languages).length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-300 mb-3">
                        Languages
                      </h3>
                      <BarChart data={stats.languages} />
                    </div>
                  )}

                  {/* Top files */}
                  {stats.top_files_by_size.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-300 mb-3">
                        Top Files by Size
                      </h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-gray-500 text-xs uppercase">
                              <th className="text-left py-2 px-3">File</th>
                              <th className="text-right py-2 px-3">Lines</th>
                              <th className="text-right py-2 px-3">Size</th>
                            </tr>
                          </thead>
                          <tbody>
                            {stats.top_files_by_size.slice(0, 5).map((f) => (
                              <tr
                                key={f.id}
                                className="border-t border-gray-800 hover:bg-gray-900/50"
                              >
                                <td className="py-2 px-3 text-gray-300 font-mono text-xs truncate max-w-xs">
                                  {f.file_name}
                                </td>
                                <td className="py-2 px-3 text-right text-gray-400">
                                  {f.line_count.toLocaleString()}
                                </td>
                                <td className="py-2 px-3 text-right text-gray-400">
                                  {(f.size_bytes / 1024).toFixed(1)} KB
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-gray-900/50 border border-gray-800 rounded-xl text-center">
                      <p className="text-2xl font-bold text-gray-200">
                        {stats.total_edges.toLocaleString()}
                      </p>
                      <p className="text-xs text-gray-500">Total Edges</p>
                    </div>
                    <div className="p-4 bg-gray-900/50 border border-gray-800 rounded-xl text-center">
                      <p className="text-2xl font-bold text-gray-200">
                        {stats.total_api_routes.toLocaleString()}
                      </p>
                      <p className="text-xs text-gray-500">API Routes</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* ── Node detail slide-in panel ──────────────────────── */}
      {selectedNodeId && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30 z-40"
            onClick={() => setSelectedNodeId(null)}
          />
          <NodeDetailPanel
            repoId={repoId}
            nodeId={selectedNodeId}
            onClose={() => setSelectedNodeId(null)}
            onSelectNode={(id) => setSelectedNodeId(id)}
            onSelectFile={(id) => {
              setSelectedFileId(id);
              setSelectedNodeId(null);
              setActiveTab("overview");
            }}
          />
        </>
      )}
    </div>
  );
}
