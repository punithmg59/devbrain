import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  FolderTree,
  Radar,
  Network,
  type LucideIcon,
} from "lucide-react";

interface WorkspaceNavProps {
  repoId: string;
  repoName?: string;
}

interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  /** Match the END of the pathname so nested routes still highlight correctly. */
  match: (pathname: string) => boolean;
}

/**
 * Top workspace navigation shared across the per-repository pages. The
 * Architecture Explorer is the first consumer; other pages can adopt it later.
 */
export default function WorkspaceNav({ repoId, repoName }: WorkspaceNavProps) {
  const { pathname } = useLocation();

  const items: NavItem[] = [
    {
      label: "Dashboard",
      to: "/dashboard",
      icon: LayoutDashboard,
      match: (p) => p === "/dashboard",
    },
    {
      label: "Repository Explorer",
      to: `/repos/${repoId}`,
      icon: FolderTree,
      match: (p) => p === `/repos/${repoId}`,
    },

    {
      label: "Impact Radar",
      to: `/repos/${repoId}/impact`,
      icon: Radar,
      match: (p) => p.endsWith("/impact"),
    },
    {
      label: "Architecture",
      to: `/repos/${repoId}/architecture`,
      icon: Network,
      match: (p) => p === `/repos/${repoId}/architecture`,
    },
  ];

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b border-white/10 bg-[#0b0b0d]/80 px-3 backdrop-blur-xl sm:px-4">
      {/* Brand */}
      <Link to="/dashboard" className="flex items-center gap-2 pr-2 sm:pr-3">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 text-sm font-bold text-white shadow-lg shadow-purple-500/20">
          DB
        </span>
        <span className="hidden text-sm font-semibold text-white sm:block">DevBrain</span>
      </Link>

      <div className="hidden h-6 w-px bg-white/10 sm:block" />

      {/* Nav items — horizontally scrollable on small screens */}
      <nav className="flex flex-1 items-center gap-1 overflow-x-auto no-scrollbar">
        {items.map((item) => {
          const active = item.match(pathname);
          const Icon = item.icon;
          return (
            <Link
              key={item.label}
              to={item.to}
              aria-current={active ? "page" : undefined}
              className={`group relative flex shrink-0 items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-all duration-200 ${
                active
                  ? "bg-white/10 text-white"
                  : "text-gray-400 hover:bg-white/5 hover:text-gray-200"
              }`}
            >
              <Icon
                className={`h-4 w-4 transition-colors ${
                  active ? "text-purple-400" : "text-gray-500 group-hover:text-gray-300"
                }`}
              />
              <span className="whitespace-nowrap">{item.label}</span>
              {active && (
                <span className="absolute -bottom-[7px] left-1/2 h-0.5 w-8 -translate-x-1/2 rounded-full bg-gradient-to-r from-purple-500 to-blue-500" />
              )}
            </Link>
          );
        })}
      </nav>

      {repoName && (
        <div className="hidden items-center gap-2 pl-2 lg:flex">
          <span className="h-6 w-px bg-white/10" />
          <span className="max-w-[220px] truncate text-xs text-gray-400" title={repoName}>
            {repoName}
          </span>
        </div>
      )}
    </header>
  );
}
