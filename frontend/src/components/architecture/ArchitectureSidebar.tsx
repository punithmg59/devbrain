import { PanelLeftClose, PanelLeftOpen, ChevronDown, ChevronRight, type LucideIcon } from "lucide-react";
import { useState } from "react";

export interface ArchitectureSubItem {
  id: string;
  label: string;
}

export interface ArchitectureCategory {
  key: string;
  label: string;
  icon: LucideIcon;
  count: number | null;
  subItems?: ArchitectureSubItem[];
}

interface ArchitectureSidebarProps {
  items: ArchitectureCategory[];
  activeKey: string;
  activeSubKey?: string | null;
  onSelect: (key: string, subKey?: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export default function ArchitectureSidebar({
  items,
  activeKey,
  activeSubKey,
  onSelect,
  collapsed,
  onToggleCollapse,
}: ArchitectureSidebarProps) {
  // Track expanded state for categories with subItems
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    request_flow: true,
    service_dependency: true,
    db_relationship: true,
  });

  const toggleExpand = (key: string) => {
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="flex h-full flex-col bg-[#0b0b0d]">
      {/* Header */}
      <div
        className={`flex h-12 shrink-0 items-center border-b border-white/10 ${
          collapsed ? "justify-center px-0" : "justify-between px-3"
        }`}
      >
        {!collapsed && (
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            Diagram Modes
          </span>
        )}
        <button
          type="button"
          onClick={onToggleCollapse}
          aria-pressed={collapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="grid h-7 w-7 place-items-center rounded-md text-gray-400 transition-colors hover:bg-white/10 hover:text-white"
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      {/* Category list */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-2 no-scrollbar">
        {items.map((item) => {
          const Icon = item.icon;
          const active = item.key === activeKey;
          const hasSubItems = item.subItems && item.subItems.length > 0;
          const isExpanded = expanded[item.key];

          return (
            <div key={item.key}>
              <button
                type="button"
                onClick={() => {
                  onSelect(item.key);
                  if (hasSubItems) toggleExpand(item.key);
                }}
                title={collapsed ? item.label : undefined}
                aria-current={active ? "true" : undefined}
                className={`group relative flex w-full items-center rounded-lg text-sm transition-all duration-200 ${
                  collapsed ? "justify-center px-0 py-2.5" : "gap-3 px-3 py-2"
                } ${
                  active && (!hasSubItems || activeSubKey === null)
                    ? "bg-gradient-to-r from-purple-500/15 to-blue-500/10 text-white"
                    : "text-gray-400 hover:bg-white/5 hover:text-gray-200"
                }`}
              >
                {active && (!hasSubItems || activeSubKey === null) && (
                  <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r bg-gradient-to-b from-purple-400 to-blue-400" />
                )}
                <Icon
                  className={`h-[18px] w-[18px] shrink-0 transition-colors ${
                    active ? "text-purple-300" : "text-gray-500 group-hover:text-gray-300"
                  }`}
                />
                {!collapsed && (
                  <>
                    <span className="truncate">{item.label}</span>
                    <span
                      className={`ml-auto rounded-md px-1.5 py-0.5 text-[11px] tabular-nums transition-colors ${
                        active
                          ? "bg-white/10 text-gray-200"
                          : "bg-white/5 text-gray-500 group-hover:text-gray-400"
                      }`}
                    >
                      {item.count ?? "—"}
                    </span>
                    {hasSubItems && (
                      <span className="ml-1 text-gray-500 hover:text-gray-300">
                        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </span>
                    )}
                  </>
                )}
              </button>

              {/* Sub items list */}
              {!collapsed && hasSubItems && isExpanded && (
                <div className="mt-1 ml-6 space-y-1 border-l border-white/10 pl-2">
                  {item.subItems!.map((sub) => {
                    const subActive = activeKey === item.key && activeSubKey === sub.id;
                    return (
                      <button
                        key={sub.id}
                        type="button"
                        onClick={() => onSelect(item.key, sub.id)}
                        className={`block w-full truncate rounded-md px-2 py-1.5 text-left text-xs transition-colors ${
                          subActive
                            ? "bg-white/10 text-purple-400"
                            : "text-gray-500 hover:bg-white/5 hover:text-gray-300"
                        }`}
                        title={sub.label}
                      >
                        {sub.label}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Footer hint */}
      {!collapsed && (
        <div className="shrink-0 border-t border-white/10 p-3">
          <p className="text-[11px] leading-relaxed text-gray-600">
            Select a diagram mode to explore the architecture graph.
          </p>
        </div>
      )}
    </div>
  );
}
