import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { Globe, Code2, Box, Server, Database, Circle, type LucideIcon } from "lucide-react";
import type { ArchNodeData } from "./graphLayout";

interface TypeStyle {
  label: string;
  icon: LucideIcon;
  ring: string; // border color
  text: string; // accent text
  dot: string; // icon color
}

const TYPE_STYLE: Record<string, TypeStyle> = {
  api_route: { label: "API", icon: Globe, ring: "border-green-500/50", text: "text-green-300", dot: "text-green-400" },
  function: { label: "Function", icon: Code2, ring: "border-blue-500/50", text: "text-blue-300", dot: "text-blue-400" },
  method: { label: "Method", icon: Code2, ring: "border-teal-500/50", text: "text-teal-300", dot: "text-teal-400" },
  class: { label: "Class", icon: Box, ring: "border-purple-500/50", text: "text-purple-300", dot: "text-purple-400" },
  service: { label: "Service", icon: Server, ring: "border-amber-500/50", text: "text-amber-300", dot: "text-amber-400" },
  database_table: { label: "Table", icon: Database, ring: "border-rose-500/50", text: "text-rose-300", dot: "text-rose-400" },
  external_api: { label: "External", icon: Globe, ring: "border-cyan-500/50", text: "text-cyan-300", dot: "text-cyan-400" },
};

const FALLBACK: TypeStyle = {
  label: "Node",
  icon: Circle,
  ring: "border-white/20",
  text: "text-gray-300",
  dot: "text-gray-400",
};

function ArchGraphNodeImpl({ data, selected }: NodeProps<ArchNodeData & { healthRisk?: number }>) {
  const style = TYPE_STYLE[data.nodeType] ?? FALLBACK;
  const Icon = style.icon;

  const focus = data.focus || selected;
  const opacity = data.dim ? "opacity-25" : "opacity-100";
  
  // Health visualization logic
  const risk = data.healthRisk;
  let riskClass = "";
  let riskBadge = null;

  if (risk !== undefined) {
    if (risk >= 75) {
      // Critical risk
      riskClass = "border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.5)] animate-pulse ring-2 ring-red-500/50";
      riskBadge = <div className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white shadow-lg">{Math.round(risk)}</div>;
    } else if (risk >= 60) {
      // High risk
      riskClass = "border-orange-500 shadow-[0_0_10px_rgba(249,115,22,0.3)] ring-1 ring-orange-500/40";
      riskBadge = <div className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-orange-500 text-[9px] font-bold text-white shadow-lg">{Math.round(risk)}</div>;
    } else if (risk >= 40) {
      // Moderate risk
      riskClass = "border-amber-500";
    }
  }

  const ring = data.match
    ? "border-yellow-400 ring-2 ring-yellow-400/40"
    : focus
    ? `border-white ring-2 ring-purple-500/40`
    : riskClass || style.ring;

  return (
    <div
      className={`relative flex h-[52px] w-[184px] items-center gap-2 rounded-lg border bg-[#15151a] px-3 shadow-lg transition-[opacity,box-shadow,border] duration-300 ${ring} ${opacity}`}
    >
      {riskBadge}
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-0 !bg-white/30" />
      <Icon className={`h-4 w-4 shrink-0 ${style.dot}`} />
      <div className="min-w-0 flex-1">
        <div className="truncate font-mono text-xs font-medium text-gray-100" title={data.label}>
          {data.label}
        </div>
        <div className={`text-[10px] uppercase tracking-wide ${style.text}`}>{style.label}</div>
      </div>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-0 !bg-white/30" />
    </div>
  );
}

export default memo(ArchGraphNodeImpl);
