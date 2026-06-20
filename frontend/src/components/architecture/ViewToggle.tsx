import { List, Share2 } from "lucide-react";

export type ArchView = "list" | "graph";

interface ViewToggleProps {
  mode: ArchView;
  onChange: (mode: ArchView) => void;
}

export default function ViewToggle({ mode, onChange }: ViewToggleProps) {
  const opts: { key: ArchView; label: string; icon: typeof List }[] = [
    { key: "list", label: "List", icon: List },
    { key: "graph", label: "Graph", icon: Share2 },
  ];
  return (
    <div className="flex items-center rounded-lg border border-white/10 bg-white/5 p-0.5">
      {opts.map((o) => {
        const Icon = o.icon;
        const active = mode === o.key;
        return (
          <button
            key={o.key}
            type="button"
            onClick={() => onChange(o.key)}
            aria-pressed={active}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              active ? "bg-white/10 text-white" : "text-gray-400 hover:text-gray-200"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
