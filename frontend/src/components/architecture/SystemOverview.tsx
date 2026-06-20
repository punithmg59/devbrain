import {
  Files,
  Code2,
  Box,
  Globe,
  Server,
  Database,
  GitBranch,
  AlertCircle,
  type LucideIcon,
} from "lucide-react";
import type { ArchitectureOverview } from "../../services/architectureService";

interface SystemOverviewProps {
  overview: ArchitectureOverview | null;
  loading: boolean;
  error: string | null;
}

interface Stat {
  label: string;
  key: keyof ArchitectureOverview;
  icon: LucideIcon;
  accent: string; // icon color
}

const STATS: Stat[] = [
  { label: "Total Files", key: "total_files", icon: Files, accent: "text-sky-400" },
  { label: "Total Functions", key: "functions", icon: Code2, accent: "text-blue-400" },
  { label: "Total Classes", key: "classes", icon: Box, accent: "text-purple-400" },
  { label: "Total APIs", key: "api_routes", icon: Globe, accent: "text-green-400" },
  { label: "Total Services", key: "backend_services", icon: Server, accent: "text-amber-400" },
  { label: "Total Database Tables", key: "database_tables", icon: Database, accent: "text-rose-400" },
  { label: "Total Dependencies", key: "total_dependencies", icon: GitBranch, accent: "text-teal-400" },
];

export default function SystemOverview({ overview, loading, error }: SystemOverviewProps) {
  return (
    <div className="flex h-full flex-col bg-[#0a0a0c]">
      <div className="shrink-0 border-b border-white/10 px-5 py-4">
        <h2 className="text-base font-semibold text-white">System Overview</h2>
        <p className="text-xs text-gray-500">High-level metrics from the repository graph.</p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-5 no-scrollbar">
        {error ? (
          <div className="flex items-center gap-2 rounded-lg border border-red-900/40 bg-red-900/10 p-4 text-sm text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {STATS.map((stat, i) => {
              const Icon = stat.icon;
              const value = overview ? overview[stat.key] : null;
              return (
                <div
                  key={stat.key}
                  style={{ animationDelay: `${i * 40}ms` }}
                  className="animate-fade-in-up rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-white/20 hover:bg-white/[0.05]"
                >
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs font-medium uppercase tracking-wide text-gray-500">
                      {stat.label}
                    </span>
                    <Icon className={`h-4 w-4 ${stat.accent}`} />
                  </div>
                  {loading || value === null ? (
                    <div className="h-9 w-16 animate-pulse rounded bg-white/10" />
                  ) : (
                    <div className="text-3xl font-semibold tabular-nums text-white">
                      {value.toLocaleString()}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
