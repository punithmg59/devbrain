import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  AlertTriangle,
  Zap,
  Activity,
  Layers,
  Repeat,
  Target,
  ShieldAlert,
  Search,
  ArrowRight,
} from "lucide-react";
import WorkspaceNav from "../components/architecture/WorkspaceNav";
import { intelligenceService, type IntelligenceDashboard } from "../services/intelligenceService";

export default function ArchitectureIntelligencePage() {
  const { repoId = "" } = useParams<{ repoId: string }>();
  const [data, setData] = useState<IntelligenceDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId) return;
    let alive = true;
    setLoading(true);
    setError(null);
    intelligenceService
      .getDashboard(repoId)
      .then((d) => {
        if (alive) setData(d);
      })
      .catch((err) => {
        if (alive) setError(err.message || "Failed to load intelligence data.");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [repoId]);

  if (loading) {
    return (
      <div className="flex h-screen flex-col bg-[#0a0a0c] text-white">
        <WorkspaceNav repoId={repoId} />
        <div className="flex flex-1 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-500 border-t-transparent" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex h-screen flex-col bg-[#0a0a0c] text-white">
        <WorkspaceNav repoId={repoId} />
        <div className="flex flex-1 items-center justify-center text-red-400">
          <ShieldAlert className="mr-2 h-6 w-6" />
          {error || "No data available."}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-[#0a0a0c] text-white">
      <WorkspaceNav repoId={repoId} />

      <main className="flex-1 overflow-y-auto px-4 py-8 sm:px-8">
        <div className="mx-auto max-w-7xl space-y-8">
          <header>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent inline-flex items-center gap-3">
              <Zap className="h-8 w-8 text-purple-400" />
              Architecture Intelligence
            </h1>
            <p className="mt-2 text-gray-400">
              Graph-powered insights and deterministic analysis of your repository's structure.
            </p>
          </header>

          {/* Top Scores Grid */}
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm relative overflow-hidden group hover:border-purple-500/30 transition-colors">
              <div className="absolute -right-4 -top-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <Target className="h-32 w-32" />
              </div>
              <h3 className="text-sm font-medium text-gray-400">Architecture Grade</h3>
              <div className="mt-2 flex items-baseline gap-2">
                <span className={`text-5xl font-bold ${getGradeColor(data.architecture_grade)}`}>
                  {data.architecture_grade}
                </span>
                <span className="text-sm text-gray-500">score: {data.architecture_score}</span>
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm relative overflow-hidden group hover:border-red-500/30 transition-colors">
              <div className="absolute -right-4 -top-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <ShieldAlert className="h-32 w-32" />
              </div>
              <h3 className="text-sm font-medium text-gray-400">Structural Risk</h3>
              <div className="mt-2 flex items-baseline gap-2">
                <span className={`text-4xl font-bold ${getRiskColor(data.risk_score)}`}>
                  {data.risk_score}
                </span>
                <span className="text-sm text-gray-500">/ 100</span>
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
              <h3 className="text-sm font-medium text-gray-400">Critical Hubs</h3>
              <div className="mt-2 text-3xl font-bold text-white">
                {data.critical_components.length}
              </div>
              <p className="mt-1 text-xs text-gray-500">Components with outsized influence</p>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
              <h3 className="text-sm font-medium text-gray-400">Detected Bottlenecks</h3>
              <div className="mt-2 text-3xl font-bold text-white">
                {data.bottlenecks.length}
              </div>
              <p className="mt-1 text-xs text-gray-500">God services & oversized modules</p>
            </div>
          </div>

          <div className="grid gap-8 lg:grid-cols-2">
            {/* Left Column */}
            <div className="space-y-8">
              {/* Critical Components */}
              <section className="rounded-xl border border-white/10 bg-[#121214] overflow-hidden">
                <div className="border-b border-white/10 bg-white/5 px-6 py-4 flex items-center gap-2">
                  <Activity className="h-5 w-5 text-blue-400" />
                  <h2 className="text-lg font-semibold text-white">Critical Components</h2>
                </div>
                <div className="divide-y divide-white/5">
                  {data.critical_components.length === 0 ? (
                    <div className="p-6 text-gray-400 text-sm">No critical hubs detected.</div>
                  ) : (
                    data.critical_components.slice(0, 5).map((comp) => (
                      <div key={comp.node_id} className="p-6 hover:bg-white/[0.02] transition-colors">
                        <div className="flex items-start justify-between">
                          <div>
                            <Link
                              to={`/repos/${repoId}/architecture?node=${comp.node_id}`}
                              className="font-mono text-sm text-purple-300 hover:underline inline-flex items-center gap-1"
                            >
                              {comp.name}
                              <ArrowRight className="h-3 w-3" />
                            </Link>
                            <p className="mt-1 text-xs text-gray-400">{comp.reason}</p>
                          </div>
                          <div className="text-right">
                            <span className="inline-flex items-center rounded-full bg-blue-500/10 px-2 py-1 text-xs font-medium text-blue-400 ring-1 ring-inset ring-blue-500/20">
                              Score: {comp.influence_score}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </section>

              {/* Refactor Opportunities */}
              <section className="rounded-xl border border-white/10 bg-[#121214] overflow-hidden">
                <div className="border-b border-white/10 bg-white/5 px-6 py-4 flex items-center gap-2">
                  <Repeat className="h-5 w-5 text-green-400" />
                  <h2 className="text-lg font-semibold text-white">Refactor Opportunities</h2>
                </div>
                <div className="divide-y divide-white/5">
                  {data.refactor_suggestions.length === 0 ? (
                    <div className="p-6 text-gray-400 text-sm">No major refactor suggestions.</div>
                  ) : (
                    data.refactor_suggestions.map((s, i) => (
                      <div key={i} className="p-6 hover:bg-white/[0.02] transition-colors">
                        <h3 className="text-sm font-medium text-gray-200">{s.title}</h3>
                        <p className="mt-1 text-xs text-gray-400">{s.description}</p>
                        <div className="mt-3 bg-white/5 rounded-md p-3">
                          <p className="text-xs text-green-300"><span className="font-semibold">Suggestion:</span> {s.recommendation}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </section>
            </div>

            {/* Right Column */}
            <div className="space-y-8">
              {/* Bottlenecks */}
              <section className="rounded-xl border border-white/10 bg-[#121214] overflow-hidden">
                <div className="border-b border-white/10 bg-white/5 px-6 py-4 flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-orange-400" />
                  <h2 className="text-lg font-semibold text-white">Bottlenecks</h2>
                </div>
                <div className="divide-y divide-white/5">
                  {data.bottlenecks.length === 0 ? (
                    <div className="p-6 text-gray-400 text-sm">No bottlenecks detected.</div>
                  ) : (
                    data.bottlenecks.slice(0, 5).map((b, i) => (
                      <div key={i} className="p-6 hover:bg-white/[0.02] transition-colors">
                        <div className="flex items-start justify-between">
                          <div>
                            <Link
                              to={`/repos/${repoId}/architecture?node=${b.node_id}`}
                              className="font-mono text-sm text-orange-300 hover:underline inline-flex items-center gap-1"
                            >
                              {b.name}
                              <ArrowRight className="h-3 w-3" />
                            </Link>
                            <div className="mt-1">
                              <span className={`inline-flex items-center rounded bg-white/10 px-1.5 py-0.5 text-xs font-medium ${b.severity === 'critical' ? 'text-red-400' : 'text-orange-400'}`}>
                                {b.bottleneck_type.replace(/_/g, ' ')}
                              </span>
                            </div>
                            <p className="mt-2 text-xs text-gray-400">{b.description}</p>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </section>

              {/* Top Findings */}
              <section className="rounded-xl border border-white/10 bg-[#121214] overflow-hidden">
                <div className="border-b border-white/10 bg-white/5 px-6 py-4 flex items-center gap-2">
                  <Search className="h-5 w-5 text-purple-400" />
                  <h2 className="text-lg font-semibold text-white">Top Architecture Findings</h2>
                </div>
                <div className="divide-y divide-white/5">
                  {data.top_findings.length === 0 ? (
                    <div className="p-6 text-gray-400 text-sm">No findings available.</div>
                  ) : (
                    data.top_findings.map((finding) => (
                      <div key={finding.rank} className="p-6 hover:bg-white/[0.02] transition-colors flex gap-4">
                        <div className="shrink-0 flex h-8 w-8 items-center justify-center rounded-full bg-purple-500/10 text-purple-400 text-sm font-bold border border-purple-500/20">
                          {finding.rank}
                        </div>
                        <div>
                          <h3 className="text-sm font-medium text-gray-200">{finding.title}</h3>
                          <p className="mt-1 text-xs text-gray-400">{finding.description}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function getGradeColor(grade: string) {
  switch (grade) {
    case "A": return "text-emerald-400";
    case "B": return "text-blue-400";
    case "C": return "text-yellow-400";
    case "D": return "text-orange-400";
    case "F": return "text-red-400";
    default: return "text-gray-400";
  }
}

function getRiskColor(score: number) {
  if (score >= 75) return "text-red-400";
  if (score >= 50) return "text-orange-400";
  if (score >= 25) return "text-yellow-400";
  return "text-emerald-400";
}
