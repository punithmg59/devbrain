import { Code2, Layers, Server, GitBranch, Activity, Shield } from "lucide-react";

interface RepositoryInsightsProps {
  language?: string;
  analysisStatus?: string;
  functions?: number;
  classes?: number;
  services?: number;
  largestFolder?: string;
  mostConnectedService?: string;
  architectureHealth?: string;
}

export default function RepositoryInsights({
  language,
  analysisStatus,
  functions,
  classes,
  services,
  largestFolder,
  mostConnectedService,
  architectureHealth,
}: RepositoryInsightsProps) {
  const insights = [
    {
      icon: Code2,
      label: "Language",
      value: language || "—",
    },
    {
      icon: Activity,
      label: "Analysis Status",
      value: analysisStatus || "—",
    },
    {
      icon: Code2,
      label: "Functions",
      value: functions?.toLocaleString() || "—",
    },
    {
      icon: Layers,
      label: "Classes",
      value: classes?.toLocaleString() || "—",
    },
    {
      icon: Server,
      label: "Services",
      value: services?.toLocaleString() || "—",
    },
    {
      icon: GitBranch,
      label: "Largest Folder",
      value: largestFolder || "—",
    },
    {
      icon: GitBranch,
      label: "Most Connected Service",
      value: mostConnectedService || "—",
    },
    {
      icon: Shield,
      label: "Architecture Health",
      value: architectureHealth || "—",
    },
  ];

  return (
    <div className="bg-gradient-to-br from-gray-900/40 to-gray-800/30 border border-gray-800/50 rounded-2xl p-6 backdrop-blur-sm">
      <h3 className="text-lg font-semibold tracking-tight mb-4">Repository Insights</h3>
      <div className="grid grid-cols-2 gap-4">
        {insights.map((insight, index) => {
          const Icon = insight.icon;
          return (
            <div key={index} className="flex items-center gap-3 p-3 bg-gray-900/30 rounded-xl">
              <div className="w-8 h-8 rounded-lg bg-gray-800/50 flex items-center justify-center">
                <Icon className="w-4 h-4 text-gray-500" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-500 mb-0.5">{insight.label}</p>
                <p className="text-sm font-medium text-gray-300 truncate">{insight.value}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
