import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Activity, ShieldAlert, GitMerge, Database, Cpu,
  ArrowRight, Box, Target, AlertTriangle, Layers, Server
} from "lucide-react";
import { getProjectBrainDashboard } from "../services/repoDetailService";
import type { ProjectBrainResponse } from "../types/projectBrain";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import NodeDetailPanel from "../components/NodeDetailPanel";

type TabType = "overview" | "architecture" | "dependencies" | "violations";

export default function ProjectBrainPage() {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<ProjectBrainResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("overview");

  // Drill-down states
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId) return;
    setLoading(true);
    getProjectBrainDashboard(repoId)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load Project Brain");
        setLoading(false);
      });
  }, [repoId]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-screen bg-[#0a0a0a]">
        <LoadingSpinner />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-screen bg-[#0a0a0a]">
        <div className="bg-red-900/20 text-red-400 p-6 rounded-xl border border-red-900/50">
          <ShieldAlert className="w-8 h-8 mb-4 mx-auto" />
          <h2 className="text-xl font-semibold text-center mb-2">Error Loading Dashboard</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const {
    intelligence_score,
    architecture_map,
    dependency_health,
    critical_functions,
    database_hotspots,
    high_risk_apis,
    architecture_violations
  } = data;

  const tabs = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "architecture", label: "Architecture", icon: Layers },
    { id: "dependencies", label: "Dependencies", icon: GitMerge },
    { id: "violations", label: "Violations", icon: ShieldAlert },
  ];

  return (
    <div className="flex-1 min-h-screen bg-[#050505] text-slate-300 font-sans p-6 overflow-y-auto">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
              <Cpu className="w-8 h-8 text-purple-500" />
              Project Brain
            </h1>
            <p className="text-slate-400 mt-1">Repository Intelligence & Architecture Health</p>
          </div>

          {/* Intelligence Score Badge */}
          <div className="flex items-center gap-4 bg-[#111] border border-[#222] rounded-2xl p-4 shadow-[0_0_20px_rgba(168,85,247,0.1)]">
            <div className="text-right">
              <div className="text-sm text-slate-400">Intelligence Score</div>
              <div className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-blue-400">
                {intelligence_score.total_score} / 100
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-[#222] pb-px">
          {tabs.map((tab) => {
            const active = activeTab === tab.id;
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-all ${active
                  ? "border-purple-500 text-purple-400 bg-purple-500/5"
                  : "border-transparent text-slate-500 hover:text-slate-300 hover:bg-white/5"
                  }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* KPI Cards row */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-[#111] border border-[#222] rounded-xl p-5 hover:border-purple-500/30 transition-colors">
                <div className="text-sm text-slate-400 mb-2 flex items-center gap-2">
                  <Box className="w-4 h-4 text-blue-400" /> Frontend Components
                </div>
                <div className="text-3xl font-bold text-white">{architecture_map.frontend_components}</div>
              </div>
              <div className="bg-[#111] border border-[#222] rounded-xl p-5 hover:border-purple-500/30 transition-colors">
                <div className="text-sm text-slate-400 mb-2 flex items-center gap-2">
                  <Server className="w-4 h-4 text-orange-400" /> Backend Services
                </div>
                <div className="text-3xl font-bold text-white">{architecture_map.backend_services}</div>
              </div>
              <div className="bg-[#111] border border-[#222] rounded-xl p-5 hover:border-purple-500/30 transition-colors">
                <div className="text-sm text-slate-400 mb-2 flex items-center gap-2">
                  <Target className="w-4 h-4 text-green-400" /> API Routes
                </div>
                <div className="text-3xl font-bold text-white">{architecture_map.api_routes}</div>
              </div>
              <div className="bg-[#111] border border-[#222] rounded-xl p-5 hover:border-purple-500/30 transition-colors">
                <div className="text-sm text-slate-400 mb-2 flex items-center gap-2">
                  <Database className="w-4 h-4 text-cyan-400" /> Database Tables
                </div>
                <div className="text-3xl font-bold text-white">{architecture_map.database_tables}</div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Critical Functions */}
              <div className="bg-[#111] border border-[#222] rounded-2xl overflow-hidden flex flex-col h-[400px]">
                <div className="p-4 border-b border-[#222] bg-white/[0.02] flex items-center justify-between">
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <Activity className="w-4 h-4 text-red-400" />
                    Critical Functions
                  </h3>
                  <span className="text-xs bg-red-500/10 text-red-400 px-2 py-1 rounded-full border border-red-500/20">
                    High Fan-In
                  </span>
                </div>
                <div className="overflow-y-auto flex-1 p-2">
                  {critical_functions.slice(0, 10).map((fn, idx) => (
                    <div
                      key={fn.node_id}
                      onClick={() => setSelectedNodeId(fn.node_id)}
                      className="group flex items-center justify-between p-3 rounded-lg hover:bg-white/5 cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-3 overflow-hidden">
                        <div className="text-slate-500 font-mono text-xs w-6">{idx + 1}</div>
                        <div className="truncate">
                          <div className="text-slate-200 font-mono text-sm truncate">{fn.name}</div>
                          <div className="text-slate-500 text-xs truncate mt-0.5">{fn.file_path}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 shrink-0">
                        <div className="text-right hidden sm:block">
                          <div className="text-xs text-slate-400">Score</div>
                          <div className="text-sm text-red-400 font-mono">{fn.importance_score}</div>
                        </div>
                        <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-purple-400 transition-colors" />
                      </div>
                    </div>
                  ))}
                  {critical_functions.length === 0 && (
                    <div className="text-center text-slate-500 py-8">No critical functions detected.</div>
                  )}
                </div>
              </div>

              {/* Database Hotspots */}
              <div className="bg-[#111] border border-[#222] rounded-2xl overflow-hidden flex flex-col h-[400px]">
                <div className="p-4 border-b border-[#222] bg-white/[0.02] flex items-center justify-between">
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <Database className="w-4 h-4 text-cyan-400" />
                    Database Hotspots
                  </h3>
                  <span className="text-xs bg-cyan-500/10 text-cyan-400 px-2 py-1 rounded-full border border-cyan-500/20">
                    Highest Activity
                  </span>
                </div>
                <div className="overflow-y-auto flex-1 p-2">
                  {database_hotspots.map((table) => (
                    <div
                      key={table.node_id}
                      onClick={() => setSelectedNodeId(table.node_id)}
                      className="group flex flex-col p-3 rounded-lg hover:bg-white/5 cursor-pointer transition-colors border-b border-[#222]/50 last:border-0"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-cyan-400 font-mono text-sm flex items-center gap-2">
                          <Database className="w-3 h-3" /> {table.name}
                        </div>
                        <div className="text-xs text-slate-500">
                          {table.touching_functions.length} functions touching
                        </div>
                      </div>
                      <div className="grid grid-cols-4 gap-2">
                        <div className="bg-black/50 rounded p-2 text-center border border-[#333]">
                          <div className="text-[10px] text-slate-500 uppercase">Reads</div>
                          <div className="text-sm text-slate-300 font-mono">{table.total_reads}</div>
                        </div>
                        <div className="bg-black/50 rounded p-2 text-center border border-[#333]">
                          <div className="text-[10px] text-slate-500 uppercase">Writes</div>
                          <div className="text-sm text-slate-300 font-mono">{table.total_writes}</div>
                        </div>
                        <div className="bg-black/50 rounded p-2 text-center border border-[#333]">
                          <div className="text-[10px] text-slate-500 uppercase">Updates</div>
                          <div className="text-sm text-slate-300 font-mono">{table.total_updates}</div>
                        </div>
                        <div className="bg-black/50 rounded p-2 text-center border border-[#333]">
                          <div className="text-[10px] text-slate-500 uppercase">Deletes</div>
                          <div className="text-sm text-slate-300 font-mono">{table.total_deletes}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                  {database_hotspots.length === 0 && (
                    <div className="text-center text-slate-500 py-8">No database hotspots detected.</div>
                  )}
                </div>
              </div>
            </div>

            {/* High Risk APIs */}
            <div className="bg-[#111] border border-[#222] rounded-2xl overflow-hidden">
              <div className="p-4 border-b border-[#222] bg-white/[0.02]">
                <h3 className="font-semibold text-white flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-orange-400" />
                  High Risk APIs
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
                {high_risk_apis.slice(0, 6).map((api) => (
                  <div
                    key={api.node_id}
                    onClick={() => navigate(`/repos/${repoId}/impact?q=${encodeURIComponent(api.name)}&scenario=modify`)}
                    className="bg-black/40 border border-[#333] hover:border-orange-500/50 p-4 rounded-xl cursor-pointer transition-all hover:bg-orange-500/5 group"
                  >
                    <div className="text-orange-400 font-mono text-sm truncate mb-1">{api.name}</div>
                    <div className="text-slate-500 text-xs truncate mb-3">{api.route_path || "Unknown Route"}</div>

                    <div className="flex items-center justify-between mt-auto">
                      <div className="flex gap-3">
                        <div className="flex flex-col">
                          <span className="text-[10px] text-slate-500">Tables</span>
                          <span className="text-slate-300 text-sm">{api.tables_touched}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[10px] text-slate-500">Functions</span>
                          <span className="text-slate-300 text-sm">{api.functions_touched}</span>
                        </div>
                      </div>
                      <div className="w-8 h-8 rounded-full bg-[#222] group-hover:bg-orange-500/20 flex items-center justify-center transition-colors">
                        <Target className="w-4 h-4 text-slate-400 group-hover:text-orange-400" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {high_risk_apis.length === 0 && (
                <div className="text-center text-slate-500 py-8">No high-risk APIs detected.</div>
              )}
            </div>

          </div>
        )}

        {/* Violations Tab Content */}
        {activeTab === "violations" && (
          <div className="bg-[#111] border border-[#222] rounded-2xl overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="p-4 border-b border-[#222] bg-white/[0.02]">
              <h3 className="font-semibold text-white flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-red-400" />
                Architecture Violations
              </h3>
            </div>
            <div className="divide-y divide-[#222]">
              {architecture_violations.map((violation) => (
                <div key={violation.id} className="p-4 hover:bg-white/5 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${violation.severity === 'Critical' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                          violation.severity === 'High' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
                            'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                          }`}>
                          {violation.severity}
                        </span>
                        <span className="text-slate-200 font-medium">{violation.rule_name}</span>
                      </div>
                      <p className="text-slate-400 text-sm">{violation.description}</p>
                      {violation.file_path && (
                        <div className="text-xs font-mono text-slate-500 mt-2 bg-black/30 p-2 rounded border border-[#333] inline-block">
                          {violation.file_path}
                        </div>
                      )}
                    </div>
                    {violation.source_node_id && (
                      <button
                        onClick={() => setSelectedNodeId(violation.source_node_id!)}
                        className="text-xs bg-[#222] hover:bg-[#333] text-slate-300 px-3 py-1.5 rounded transition-colors"
                      >
                        Inspect Source
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {architecture_violations.length === 0 && (
                <div className="text-center text-slate-500 py-12">
                  <ShieldAlert className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                  <p>No architecture violations found! Great job.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Dependencies Tab Content */}
        {activeTab === "dependencies" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-[#111] border border-[#222] rounded-2xl p-6 flex flex-col items-center justify-center h-48">
              <div className="text-5xl font-bold text-green-400 mb-2">{dependency_health.healthy}</div>
              <div className="text-slate-400 text-sm">Healthy Edges</div>
            </div>
            <div className="bg-[#111] border border-[#222] rounded-2xl p-6 flex flex-col items-center justify-center h-48">
              <div className="text-5xl font-bold text-yellow-400 mb-2">{dependency_health.risky}</div>
              <div className="text-slate-400 text-sm">Risky Components</div>
            </div>
            <div className="bg-[#111] border border-[#222] rounded-2xl p-6 flex flex-col items-center justify-center h-48">
              <div className="text-5xl font-bold text-slate-500 mb-2">{dependency_health.orphaned}</div>
              <div className="text-slate-400 text-sm">Orphaned Nodes</div>
            </div>
          </div>
        )}

        {/* Architecture Tab Content */}
        {activeTab === "architecture" && (
          <div className="bg-[#111] border border-[#222] rounded-2xl p-8 flex flex-col items-center justify-center min-h-[400px] text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
            <Layers className="w-16 h-16 text-slate-600 mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Architecture Map</h2>
            <p className="text-slate-400 max-w-md">
              The detailed visual architecture map requires the graph visualization library.
              For now, use the Project Brain Overview to see system layers numerically.
            </p>
          </div>
        )}

      </div>

      {/* Node Detail Overlay */}
      {selectedNodeId && repoId && (
        <NodeDetailPanel
          repoId={repoId}
          nodeId={selectedNodeId}
          onClose={() => setSelectedNodeId(null)}
          onSelectNode={(id) => setSelectedNodeId(id)}
        />
      )}
    </div>
  );
}
