import { useMemo, useState } from "react";
import { Search, SearchX, Loader2, FileCode2, Inbox } from "lucide-react";
import NodeTypeBadge from "../NodeTypeBadge";
import type { ArchNodeSummary } from "../../services/architectureService";

interface ComponentListProps {
  label: string;
  items: ArchNodeSummary[];
  loading: boolean;
  error: string | null;
  selectedId: string | null;
  onSelect: (node: ArchNodeSummary) => void;
  headerRight?: React.ReactNode;
}

/**
 * Center panel — a searchable list of the selected category's entities.
 * Reads straight from the architecture/components API (no AI, no diagram).
 */
export default function ComponentList({
  label,
  items,
  loading,
  error,
  selectedId,
  onSelect,
  headerRight,
}: ComponentListProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (n) =>
        n.name.toLowerCase().includes(q) ||
        (n.file_path ?? "").toLowerCase().includes(q)
    );
  }, [items, query]);

  return (
    <div className="flex h-full flex-col bg-[#0a0a0c]">
      {/* Header + search */}
      <div className="shrink-0 border-b border-white/10 px-4 py-3">
        <div className="mb-3 flex items-center gap-2">
          <h2 className="text-sm font-semibold text-white">{label}</h2>
          {!loading && !error && (
            <span className="rounded-md bg-white/5 px-2 py-0.5 text-[11px] tabular-nums text-gray-400">
              {filtered.length}
              {filtered.length !== items.length ? ` / ${items.length}` : ""}
            </span>
          )}
          {headerRight && <div className="ml-auto">{headerRight}</div>}
        </div>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Search ${label.toLowerCase()}…`}
            className="w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-sm text-white placeholder:text-gray-600 outline-none transition-colors focus:border-purple-500/50 focus:bg-white/[0.07]"
          />
        </div>
      </div>

      {/* Body */}
      <div className="min-h-0 flex-1 overflow-y-auto p-2 no-scrollbar">
        {loading ? (
          <ListSkeleton />
        ) : error ? (
          <CenteredState
            icon={<SearchX className="h-6 w-6 text-red-400" />}
            title="Couldn’t load components"
            sub={error}
          />
        ) : items.length === 0 ? (
          <CenteredState
            icon={<Inbox className="h-6 w-6 text-gray-500" />}
            title="Nothing here yet"
            sub={`No ${label.toLowerCase()} found in this repository.`}
          />
        ) : filtered.length === 0 ? (
          <CenteredState
            icon={<SearchX className="h-6 w-6 text-gray-500" />}
            title="No matches"
            sub={`Nothing matches “${query}”.`}
          />
        ) : (
          <ul className="space-y-1">
            {filtered.map((node) => {
              const active = node.id === selectedId;
              return (
                <li key={node.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(node)}
                    className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors ${
                      active
                        ? "bg-gradient-to-r from-purple-500/15 to-blue-500/10 ring-1 ring-purple-500/30"
                        : "hover:bg-white/5"
                    }`}
                  >
                    <FileCode2
                      className={`h-4 w-4 shrink-0 ${
                        active ? "text-purple-300" : "text-gray-600 group-hover:text-gray-400"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate font-mono text-sm text-gray-100">{node.name}</span>
                        {node.http_method && (
                          <span className="shrink-0 rounded bg-green-900/40 px-1.5 py-0.5 text-[10px] font-semibold text-green-400">
                            {node.http_method}
                          </span>
                        )}
                      </div>
                      {node.file_path && (
                        <p className="truncate text-[11px] text-gray-500" title={node.file_path}>
                          {node.file_path}
                        </p>
                      )}
                    </div>
                    <NodeTypeBadge type={node.node_type} />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

function CenteredState({
  icon,
  title,
  sub,
}: {
  icon: React.ReactNode;
  title: string;
  sub?: string;
}) {
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

function ListSkeleton() {
  return (
    <div className="space-y-1">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 rounded-lg px-3 py-2.5">
          <Loader2 className="h-4 w-4 animate-spin text-gray-700" />
          <div className="flex-1 space-y-1.5">
            <div className="h-2.5 w-1/3 rounded bg-white/5" />
            <div className="h-2 w-1/2 rounded bg-white/[0.03]" />
          </div>
        </div>
      ))}
    </div>
  );
}
