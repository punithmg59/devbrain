import { useEffect, useState, useMemo } from "react";
import { ArrowLeft, ArrowRight, Sparkles, X, Activity, Database, Server, Key, Box, FileCode, ShieldAlert, GitMerge } from "lucide-react";
import { getNodeDependencies, summarizeNode } from "../services/repoDetailService";
import type { NodeDependenciesResponse, NodeRelation } from "../types/repo";
import LoadingSpinner from "./ui/LoadingSpinner";

interface NodeDetailPanelProps {
  repoId: string;
  nodeId: string;
  onClose: () => void;
  onSelectNode?: (nodeId: string) => void;
  onSelectFile?: (fileId: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
  function: "bg-blue-900/40 text-blue-400 border-blue-700/40",
  class: "bg-purple-900/40 text-purple-400 border-purple-700/40",
  method: "bg-teal-900/40 text-teal-400 border-teal-700/40",
  api_route: "bg-green-900/40 text-green-400 border-green-700/40",
};

const RISK_COLORS: Record<string, string> = {
  low: "text-green-400",
  medium: "text-yellow-400",
  high: "text-orange-400",
  critical: "text-red-400",
};

function highlightCode(code: string): JSX.Element[] {
  const keywords = new Set([
    "def", "class", "return", "if", "else", "elif", "for", "while", "import",
    "from", "async", "await", "try", "except", "finally", "with", "as", "yield",
    "raise", "pass", "break", "continue", "lambda", "not", "and", "or", "in",
    "is", "True", "False", "None",
    "function", "const", "let", "var", "export", "default", "interface", "type",
    "extends", "implements", "new", "this", "super", "throw", "catch",
  ]);

  return code.split("\n").map((line, i) => (
    <div key={i} className="flex">
      <span className="select-none text-gray-700 w-10 text-right pr-3 shrink-0">
        {i + 1}
      </span>
      <span>
        {line.split(/(\b\w+\b)/).map((token, j) =>
          keywords.has(token) ? (
            <span key={j} className="text-purple-400 font-medium">
              {token}
            </span>
          ) : /^"[^"]*"$|^'[^']*'$/.test(token) ? (
            <span key={j} className="text-green-400">
              {token}
            </span>
          ) : (
            <span key={j}>{token}</span>
          )
        )}
      </span>
    </div>
  ));
}

function RelationList({
  label,
  icon,
  items,
  onSelect,
}: {
  label: string;
  icon?: JSX.Element;
  items: NodeRelation[];
  onSelect?: (id: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mt-6 border-t border-gray-800/50 pt-4">
      <div className="flex items-center gap-2 mb-3">
        {icon && <div className="text-gray-500">{icon}</div>}
        <p className="text-xs font-bold text-gray-300 uppercase tracking-widest">
          {label}
        </p>
        <span className="text-xs font-medium bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">
          {items.length}
        </span>
      </div>
      <div className="space-y-1.5">
        {items.map((item) => (
          <button
            key={item.node_id}
            onClick={() => onSelect?.(item.node_id)}
            className="w-full text-left flex items-center gap-2 px-3 py-2 bg-[#0f0f0f] border border-gray-800/50 rounded-lg hover:border-purple-600/50 hover:bg-purple-900/10 hover:shadow-lg transition-all group"
          >
            <ArrowRight className="w-3.5 h-3.5 text-gray-600 group-hover:text-purple-400 transition-colors shrink-0" />
            <div className="min-w-0">
              <span className="text-[13px] text-gray-200 font-medium">{item.name}</span>
              <span className="ml-2 text-[10px] text-gray-500 font-mono tracking-wide uppercase">{item.type}</span>
              {item.file_path && (
                <p className="text-[10px] text-gray-600 truncate mt-0.5">{item.file_path}</p>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function MiniDependencyMap({ data }: { data: NodeDependenciesResponse }) {
  const calledByCount = data.called_by.length + data.api_routes.length;
  const callsCount = data.calls.length + data.reads_tables.length + data.writes_tables.length + data.updates_tables.length + data.deletes_tables.length + data.services.length;

  return (
    <div className="bg-[#0a0a0a] border border-gray-800/80 rounded-xl p-4 flex flex-col items-center justify-center my-6 shadow-inner relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-blue-900/5 via-transparent to-purple-900/5 pointer-events-none" />
      
      {/* Top Nodes */}
      <div className="flex flex-col items-center z-10">
        <div className="px-3 py-1 bg-gray-900/80 border border-gray-700/50 rounded-full text-xs font-semibold text-gray-300 shadow-sm backdrop-blur-sm">
          {calledByCount} Inbound
        </div>
        <div className="h-6 w-px bg-gradient-to-b from-gray-700 to-blue-500 my-1" />
      </div>

      {/* Center Node */}
      <div className="z-10 px-4 py-2 bg-gradient-to-r from-blue-900/40 to-purple-900/40 border border-blue-700/50 rounded-lg shadow-[0_0_15px_rgba(59,130,246,0.1)] backdrop-blur-sm">
        <span className="text-sm font-bold text-gray-100">{data.node.name}</span>
      </div>

      {/* Bottom Nodes */}
      <div className="flex flex-col items-center z-10">
        <div className="h-6 w-px bg-gradient-to-b from-purple-500 to-gray-700 my-1" />
        <div className="px-3 py-1 bg-gray-900/80 border border-gray-700/50 rounded-full text-xs font-semibold text-gray-300 shadow-sm backdrop-blur-sm">
          {callsCount} Outbound
        </div>
      </div>
    </div>
  );
}

export default function NodeDetailPanel({
  repoId,
  nodeId: initialNodeId,
  onClose,
  onSelectNode: _onSelectNode,
  onSelectFile: _onSelectFile,
}: NodeDetailPanelProps) {
  const [historyStack, setHistoryStack] = useState<string[]>([initialNodeId]);
  const currentNodeId = historyStack[historyStack.length - 1];

  const [data, setData] = useState<NodeDependenciesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [summarizing, setSummarizing] = useState(false);

  useEffect(() => {
    // Reset history if the panel is opened with a completely new initial node
    if (historyStack.length > 0 && historyStack[0] !== initialNodeId && historyStack.indexOf(initialNodeId) === -1) {
       setHistoryStack([initialNodeId]);
    }
  }, [initialNodeId]);

  useEffect(() => {
    setLoading(true);
    getNodeDependencies(repoId, currentNodeId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [repoId, currentNodeId]);

  const handleNavigate = (id: string) => {
    setHistoryStack(prev => [...prev, id]);
  };

  const handleBack = () => {
    setHistoryStack(prev => prev.length > 1 ? prev.slice(0, -1) : prev);
  };

  const handleSummarize = async () => {
    if (!data) return;
    setSummarizing(true);
    try {
      const res = await summarizeNode(repoId, data.node.id);
      setData((prev) =>
        prev
          ? {
              ...prev,
              node: {
                ...prev.node,
                summary: res.summary,
                tags: res.tags,
                detailed_explanation: res.detailed_explanation ?? prev.node.detailed_explanation,
                architecture_role: res.architecture_role ?? prev.node.architecture_role,
                complexity_level: res.complexity_level ?? prev.node.complexity_level,
                call_flow_diagram: res.call_flow_diagram ?? prev.node.call_flow_diagram,
                ai_tags: res.ai_tags ?? prev.node.ai_tags,
                potential_risks: res.potential_risks ?? prev.node.potential_risks,
                dependencies: res.dependencies ?? prev.node.dependencies,
                responsibilities: res.responsibilities ?? prev.node.responsibilities,
                inputs: res.inputs ?? prev.node.inputs,
                outputs: res.outputs ?? prev.node.outputs,
                related_components: res.related_components ?? prev.node.related_components,
                call_flow: res.call_flow ?? prev.node.call_flow,
              },
            }
          : prev
      );
    } catch {
      // silent
    } finally {
      setSummarizing(false);
    }
  };

  const dbUsageItems = useMemo(() => {
    if (!data) return [];
    return [
      ...data.reads_tables.map(n => ({ ...n, action: "Read" })),
      ...data.writes_tables.map(n => ({ ...n, action: "Write" })),
      ...data.updates_tables.map(n => ({ ...n, action: "Update" })),
      ...data.deletes_tables.map(n => ({ ...n, action: "Delete" })),
    ].map(n => ({ ...n, type: `${n.action} Table` }));
  }, [data]);

  return (
    <div className="fixed right-0 top-0 w-[500px] h-screen bg-[#0d0d0e] border-l border-gray-800 z-50 overflow-y-auto shadow-2xl flex flex-col">
      {/* Fixed Header */}
      <div className="sticky top-0 bg-[#0d0d0e]/95 backdrop-blur z-20 border-b border-gray-800/80 px-6 py-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {historyStack.length > 1 && (
              <button
                onClick={handleBack}
                className="p-1 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors"
                title="Go back"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
            )}
            <h2 className="text-xl font-bold text-white tracking-tight break-all">
              {data?.node?.name || "Loading..."}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-500 hover:text-white hover:bg-gray-800 rounded transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {data && (
          <div className="flex items-center gap-2 ml={historyStack.length > 1 ? '9' : '0'}">
            <span className={`px-2 py-0.5 text-xs font-semibold rounded border ${TYPE_COLORS[data.node.node_type] ?? "bg-gray-800 text-gray-400 border-gray-700"}`}>
              {data.node.node_type}
            </span>
            {data.node.is_async && (
              <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase bg-yellow-900/30 text-yellow-500 border border-yellow-700/30 rounded">
                async
              </span>
            )}
            {data.node.is_exported && (
              <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase bg-emerald-900/30 text-emerald-500 border border-emerald-700/30 rounded">
                exported
              </span>
            )}
          </div>
        )}
      </div>

      <div className="flex-1 p-6 pt-4">
        {loading ? (
          <div className="flex-1 flex items-center justify-center h-64">
            <LoadingSpinner text="Analyzing dependencies..." />
          </div>
        ) : !data ? (
          <div className="text-center text-gray-500 mt-20">Node not found</div>
        ) : (
          <div className="space-y-6">
            
            {/* Overview / Risk Engine */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[#121212] border border-gray-800 rounded-xl p-4 flex flex-col justify-between">
                <div className="flex items-center gap-2 text-gray-400 mb-1">
                  <ShieldAlert className="w-4 h-4" />
                  <span className="text-xs font-semibold uppercase tracking-wider">Risk Score</span>
                </div>
                <div className="mt-2">
                  <div className="flex items-baseline gap-2">
                    <span className={`text-3xl font-black ${RISK_COLORS[data.risk.level]}`}>
                      {data.risk.score}
                    </span>
                    <span className={`text-xs font-bold uppercase tracking-wider ${RISK_COLORS[data.risk.level]}`}>
                      {data.risk.level}
                    </span>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-1 leading-tight">{data.risk.reason}</p>
                </div>
              </div>

              <div className="bg-[#121212] border border-gray-800 rounded-xl p-4 flex flex-col gap-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Dependencies</span>
                  <span className="text-sm font-bold text-gray-200">{data.calls.length + data.called_by.length}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Affected APIs</span>
                  <span className="text-sm font-bold text-gray-200">{data.api_routes.length}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Affected Tables</span>
                  <span className="text-sm font-bold text-gray-200">{dbUsageItems.length}</span>
                </div>
              </div>
            </div>

            <MiniDependencyMap data={data} />

            <div className="space-y-2">
              <RelationList label="API Routes" icon={<Server className="w-4 h-4" />} items={data.api_routes} onSelect={handleNavigate} />
              <RelationList label="Called By" icon={<ArrowLeft className="w-4 h-4" />} items={data.called_by} onSelect={handleNavigate} />
              <RelationList label="Calls" icon={<ArrowRight className="w-4 h-4" />} items={data.calls} onSelect={handleNavigate} />
              <RelationList label="Database Usage" icon={<Database className="w-4 h-4" />} items={dbUsageItems} onSelect={handleNavigate} />
              <RelationList label="Services" icon={<Activity className="w-4 h-4" />} items={data.services} onSelect={handleNavigate} />
              <RelationList label="Authentication" icon={<Key className="w-4 h-4" />} items={data.auth_dependencies} onSelect={handleNavigate} />
              <RelationList label="Dependency Injection" icon={<Box className="w-4 h-4" />} items={data.dependency_injections} onSelect={handleNavigate} />
              <RelationList label="Inheritance" icon={<GitMerge className="w-4 h-4" />} items={data.inherits} onSelect={handleNavigate} />
              <RelationList label="Imports" icon={<FileCode className="w-4 h-4" />} items={data.imports} onSelect={handleNavigate} />
              <RelationList label="Contained In" items={data.contains} onSelect={handleNavigate} />
            </div>

            {/* Source Code */}
            {data.node.raw_code && (
              <div className="mt-8 border-t border-gray-800/50 pt-6">
                <p className="text-xs font-bold text-gray-300 uppercase tracking-widest mb-3">
                  Source Code
                </p>
                <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl overflow-hidden shadow-inner">
                  <div className="bg-[#151515] px-4 py-2 border-b border-gray-800 flex justify-between items-center">
                    <span className="text-[11px] font-mono text-gray-400 truncate">{data.node.full_path}</span>
                  </div>
                  <pre className="p-4 text-[13px] font-mono text-gray-300 max-h-[400px] overflow-auto leading-relaxed">
                    {highlightCode(data.node.raw_code)}
                  </pre>
                </div>
              </div>
            )}

            {/* AI Summary */}
            <div className="mt-8 border-t border-gray-800/50 pt-6">
              <div className="flex items-center justify-between mb-4">
                <p className="text-xs font-bold text-gray-300 uppercase tracking-widest flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-400" /> AI Summary
                </p>
                <button
                  onClick={handleSummarize}
                  disabled={summarizing}
                  className="px-3 py-1.5 bg-purple-600/10 text-purple-400 border border-purple-700/30 rounded hover:bg-purple-600/20 disabled:opacity-50 transition-colors text-xs font-semibold tracking-wide"
                >
                  {summarizing ? "Generating..." : "Generate Insights"}
                </button>
              </div>

              {data.node.summary ? (
                <div className="bg-gradient-to-br from-[#121212] to-[#0a0a0a] border border-gray-800 rounded-xl p-5 shadow-lg">
                  <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-line mb-4">
                    {data.node.summary}
                  </p>
                  
                  {data.node.potential_risks && (
                    <div className="mt-4 p-4 bg-red-950/20 border border-red-900/50 rounded-lg">
                      <p className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                        <ShieldAlert className="w-3.5 h-3.5" /> Potential Risks
                      </p>
                      <p className="text-[13px] text-gray-300 whitespace-pre-line leading-relaxed">
                        {data.node.potential_risks}
                      </p>
                    </div>
                  )}

                  {data.node.ai_tags && data.node.ai_tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-4">
                      {data.node.ai_tags.map(tag => (
                        <span key={tag} className="px-2 py-1 text-[10px] font-bold tracking-wide uppercase bg-purple-900/20 text-purple-300 border border-purple-700/30 rounded-md">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center p-8 border border-dashed border-gray-800 rounded-xl bg-[#0a0a0a]">
                  <Sparkles className="w-8 h-8 text-gray-600 mx-auto mb-3" />
                  <p className="text-sm text-gray-400">
                    Generate an AI-powered summary to surface key behavior, intent, and risk for this node.
                  </p>
                </div>
              )}
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
