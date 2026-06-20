import {
  PanelRightClose,
  MousePointerClick,
  Loader2,
  AlertCircle,
  ArrowDownLeft,
  ArrowUpRight,
  Package,
  Server,
  Database,
  FileCode2,
} from "lucide-react";
import NodeTypeBadge from "../NodeTypeBadge";
import type {
  ArchNodeSummary,
  NodeDetails,
  RelatedNode,
} from "../../services/architectureService";

interface DetailsPanelProps {
  onClose: () => void;
  selected: ArchNodeSummary | null;
  details: NodeDetails | null;
  loading: boolean;
  error: string | null;
  health: any | null;
  onSelectRelated: (node: ArchNodeSummary) => void;
}

/**
 * Right panel — architecture details for the selected entity.
 * Pure read of the architecture/node API: callers, callees, dependencies,
 * services and tables. No AI, no generated explanations.
 */
export default function DetailsPanel({
  onClose,
  selected,
  details,
  loading,
  error,
  health,
  onSelectRelated,
}: DetailsPanelProps) {
  return (
    <div className="flex h-full flex-col bg-[#0b0b0d]">
      {/* Header */}
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-white/10 px-3">
        <span className="text-sm font-medium text-white">Details</span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close details panel"
          className="grid h-7 w-7 place-items-center rounded-md text-gray-400 transition-colors hover:bg-white/10 hover:text-white"
        >
          <PanelRightClose className="h-4 w-4" />
        </button>
      </div>

      {/* Body */}
      <div className="min-h-0 flex-1 overflow-y-auto no-scrollbar">
        {!selected ? (
          <EmptyState />
        ) : (
          <div key={selected.id} className="animate-fade-in p-4">
            {/* Identity: Name / Type / File */}
            <div className="mb-4">
              <div className="mb-2 flex items-start justify-between gap-2">
                <h3 className="break-words font-mono text-base font-semibold text-white">
                  {selected.name}
                </h3>
                <NodeTypeBadge type={selected.node_type} />
              </div>
              {(details?.file_path ?? selected.file_path) && (
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <FileCode2 className="h-3.5 w-3.5 shrink-0" />
                  <span className="break-all" title={details?.file_path ?? selected.file_path ?? ""}>
                    {details?.file_path ?? selected.file_path}
                  </span>
                </div>
              )}
              {(selected.start_line || selected.route_path) && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {selected.http_method && (
                    <Tag>{selected.http_method} {selected.route_path}</Tag>
                  )}
                  {selected.is_async && <Tag>async</Tag>}
                  {selected.is_exported && <Tag>exported</Tag>}
                  {selected.start_line != null && (
                    <Tag>
                      L{selected.start_line}
                      {selected.end_line ? `–${selected.end_line}` : ""}
                    </Tag>
                  )}
                </div>
              )}
            </div>

            {/* Health Metrics & Impact */}
            {health && selected && (() => {
              const hotspot = health.hotspots?.find((h: any) => h.node_id === selected.id);
              if (!hotspot && !details) return null;

              const impactCallers = details?.callers.length || 0;
              const impactServices = details?.services.length || 0;
              const impactTables = details?.tables.length || 0;

              return (
                <div className="mb-4 space-y-2 rounded-lg border border-white/10 bg-white/[0.02] p-3">
                  {hotspot && (
                    <div className="mb-3 rounded border border-red-900/40 bg-red-950/30 p-2 text-xs">
                      <div className="flex items-center gap-1.5 font-semibold text-red-400">
                        <AlertCircle className="h-3.5 w-3.5" />
                        Architecture Risk: {Math.round(hotspot.score)}
                      </div>
                      <p className="mt-1 text-red-300/80">{hotspot.reason}</p>
                    </div>
                  )}
                  {details && (
                    <div className="text-[11px] text-gray-400">
                      <div className="mb-1 font-semibold text-gray-300 uppercase tracking-wider">Impact Summary</div>
                      <p>Changing this node affects:</p>
                      <ul className="mt-1 list-inside list-disc space-y-0.5 text-gray-500">
                        <li>{impactCallers} dependent {impactCallers === 1 ? 'component' : 'components'}</li>
                        <li>{impactServices} downstream {impactServices === 1 ? 'service' : 'services'}</li>
                        <li>{impactTables} database {impactTables === 1 ? 'table' : 'tables'}</li>
                      </ul>
                    </div>
                  )}
                </div>
              );
            })()}

            {loading ? (
              <RelationsSkeleton />
            ) : error ? (
              <div className="flex items-center gap-2 rounded-lg border border-red-900/40 bg-red-900/10 p-3 text-xs text-red-400">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {error}
              </div>
            ) : details ? (
              <div className="space-y-4">
                <RelationSection
                  title="Callers"
                  hint="called by"
                  icon={<ArrowDownLeft className="h-3.5 w-3.5" />}
                  nodes={details.callers}
                  onSelect={onSelectRelated}
                />
                <RelationSection
                  title="Callees"
                  hint="calls"
                  icon={<ArrowUpRight className="h-3.5 w-3.5" />}
                  nodes={details.callees}
                  onSelect={onSelectRelated}
                />
                <RelationSection
                  title="Dependencies"
                  hint="imports / injects / inherits"
                  icon={<Package className="h-3.5 w-3.5" />}
                  nodes={details.dependencies}
                  onSelect={onSelectRelated}
                />
                {details.services.length > 0 && (
                  <RelationSection
                    title="Services"
                    hint="uses"
                    icon={<Server className="h-3.5 w-3.5" />}
                    nodes={details.services}
                    onSelect={onSelectRelated}
                  />
                )}
                {details.tables.length > 0 && (
                  <RelationSection
                    title="Database Tables"
                    hint="reads / writes"
                    icon={<Database className="h-3.5 w-3.5" />}
                    nodes={details.tables}
                    onSelect={onSelectRelated}
                  />
                )}
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

function RelationSection({
  title,
  hint,
  icon,
  nodes,
  onSelect,
}: {
  title: string;
  hint: string;
  icon: React.ReactNode;
  nodes: (ArchNodeSummary | RelatedNode)[];
  onSelect: (node: ArchNodeSummary) => void;
}) {
  return (
    <section>
      <div className="mb-1.5 flex items-center gap-1.5 text-gray-400">
        <span className="text-gray-500">{icon}</span>
        <h4 className="text-xs font-semibold uppercase tracking-wide">{title}</h4>
        <span className="rounded bg-white/5 px-1.5 text-[10px] tabular-nums text-gray-500">
          {nodes.length}
        </span>
        <span className="ml-auto text-[10px] text-gray-600">{hint}</span>
      </div>
      {nodes.length === 0 ? (
        <p className="px-1 pb-1 text-xs text-gray-600">None</p>
      ) : (
        <ul className="space-y-1">
          {nodes.map((n, i) => {
            const edgeType = "edge_type" in n ? n.edge_type : null;
            return (
              <li key={`${n.id}-${i}`}>
                <button
                  type="button"
                  onClick={() => onSelect(n)}
                  className="group flex w-full items-center gap-2 rounded-md border border-white/5 bg-white/[0.02] px-2.5 py-1.5 text-left transition-colors hover:border-white/10 hover:bg-white/5"
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-mono text-xs text-gray-200">{n.name}</div>
                    {n.file_path && (
                      <div className="truncate text-[10px] text-gray-600">{n.file_path}</div>
                    )}
                  </div>
                  {edgeType && (
                    <span className="shrink-0 rounded bg-white/5 px-1.5 py-0.5 text-[9px] text-gray-400">
                      {edgeType}
                    </span>
                  )}
                  <NodeTypeBadge type={n.node_type} />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[10px] text-gray-400">
      {children}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-6 text-center">
      <div className="mb-4 grid h-12 w-12 place-items-center rounded-xl border border-white/10 bg-white/5">
        <MousePointerClick className="h-5 w-5 text-gray-500" />
      </div>
      <h3 className="mb-1 text-sm font-semibold text-gray-300">Nothing selected</h3>
      <p className="text-xs leading-relaxed text-gray-500">
        Select an entity from the list to inspect its file, callers, callees, and dependencies here.
      </p>
    </div>
  );
}

function RelationsSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, s) => (
        <div key={s}>
          <div className="mb-2 h-2.5 w-24 rounded bg-white/5" />
          <div className="space-y-1">
            {Array.from({ length: 2 }).map((__, i) => (
              <div key={i} className="h-8 rounded-md bg-white/[0.03]" />
            ))}
          </div>
        </div>
      ))}
      <div className="flex items-center gap-2 pt-1 text-xs text-gray-600">
        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading relationships…
      </div>
    </div>
  );
}
