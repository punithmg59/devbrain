import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Loader2,
  Globe,
  Workflow,
  Server,
  Database,
  ShieldAlert,
  Compass,
  Zap,
  ExternalLink,
  type LucideIcon,
} from "lucide-react";
import WorkspaceNav from "../components/architecture/WorkspaceNav";
import {
  architectureService,
  type ArchitectureStory,
  type StoryChapter,
} from "../services/architectureService";

/* ── Chapter icon + accent mapping ─────────────────────────────────── */
interface ChapterTheme {
  icon: LucideIcon;
  accent: string;      // tailwind text-*
  accentBg: string;    // tailwind bg-*
  accentBorder: string; // tailwind border-*
  gradient: string;     // CSS gradient for the header badge
}

const CHAPTER_THEMES: ChapterTheme[] = [
  {
    icon: Globe,
    accent: "text-blue-400",
    accentBg: "bg-blue-500/10",
    accentBorder: "border-blue-500/20",
    gradient: "linear-gradient(135deg, #3b82f6, #6366f1)",
  },
  {
    icon: Workflow,
    accent: "text-purple-400",
    accentBg: "bg-purple-500/10",
    accentBorder: "border-purple-500/20",
    gradient: "linear-gradient(135deg, #8b5cf6, #a855f7)",
  },
  {
    icon: Server,
    accent: "text-emerald-400",
    accentBg: "bg-emerald-500/10",
    accentBorder: "border-emerald-500/20",
    gradient: "linear-gradient(135deg, #10b981, #34d399)",
  },
  {
    icon: Database,
    accent: "text-cyan-400",
    accentBg: "bg-cyan-500/10",
    accentBorder: "border-cyan-500/20",
    gradient: "linear-gradient(135deg, #06b6d4, #22d3ee)",
  },
  {
    icon: Zap,
    accent: "text-amber-400",
    accentBg: "bg-amber-500/10",
    accentBorder: "border-amber-500/20",
    gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
  },
  {
    icon: ShieldAlert,
    accent: "text-red-400",
    accentBg: "bg-red-500/10",
    accentBorder: "border-red-500/20",
    gradient: "linear-gradient(135deg, #ef4444, #f87171)",
  },
  {
    icon: Compass,
    accent: "text-violet-400",
    accentBg: "bg-violet-500/10",
    accentBorder: "border-violet-500/20",
    gradient: "linear-gradient(135deg, #7c3aed, #a78bfa)",
  },
];

function getTheme(idx: number): ChapterTheme {
  return CHAPTER_THEMES[idx % CHAPTER_THEMES.length];
}

/* ── Main Page ─────────────────────────────────────────────────────── */
export default function StoryModePage() {
  const { repoId = "" } = useParams<{ repoId: string }>();
  const navigate = useNavigate();

  const [story, setStory] = useState<ArchitectureStory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeChapter, setActiveChapter] = useState(0);

  useEffect(() => {
    if (!repoId) return;
    let alive = true;
    setLoading(true);
    setError(null);
    architectureService
      .getStory(repoId)
      .then((data) => {
        if (alive) {
          setStory(data);
          setActiveChapter(0);
        }
      })
      .catch(() => {
        if (alive) setError("Failed to load architecture story. Ensure the repository has been analyzed.");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [repoId]);

  const chapters = story?.chapters ?? [];
  const chapter = chapters[activeChapter] as StoryChapter | undefined;
  const theme = getTheme(activeChapter);

  const goTo = useCallback(
    (idx: number) => {
      if (idx >= 0 && idx < chapters.length) setActiveChapter(idx);
    },
    [chapters.length],
  );

  const navigateToGraph = (queryParam: string, value: string) => {
    navigate(`/repos/${repoId}/architecture?${queryParam}=${encodeURIComponent(value)}`);
  };

  /* ── Loading State ─────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="flex h-screen flex-col overflow-hidden bg-[#0a0a0c] text-white">
        <WorkspaceNav repoId={repoId} />
        <div className="flex flex-1 items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
            <p className="text-sm text-gray-400 animate-pulse">Generating architecture story…</p>
          </div>
        </div>
      </div>
    );
  }

  /* ── Error State ────────────────────────────────────────────────────── */
  if (error || !story) {
    return (
      <div className="flex h-screen flex-col overflow-hidden bg-[#0a0a0c] text-white">
        <WorkspaceNav repoId={repoId} />
        <div className="flex flex-1 items-center justify-center">
          <div className="max-w-md rounded-xl border border-red-900/40 bg-red-950/20 p-8 text-center">
            <ShieldAlert className="mx-auto mb-4 h-10 w-10 text-red-400" />
            <h2 className="mb-2 text-lg font-semibold text-white">Story Generation Failed</h2>
            <p className="text-sm text-gray-400">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  const progress = chapters.length > 0 ? ((activeChapter + 1) / chapters.length) * 100 : 0;

  /* ── Main layout ───────────────────────────────────────────────────── */
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#0a0a0c] text-white">
      <WorkspaceNav repoId={repoId} />

      <div className="flex min-h-0 flex-1">
        {/* ═══════════════════════ Left Panel: Chapter Nav ═══════════════════════ */}
        <aside className="hidden w-72 shrink-0 flex-col border-r border-white/10 bg-[#0b0b0d] md:flex">
          {/* Header */}
          <div className="border-b border-white/10 p-4">
            <div className="flex items-center gap-2.5">
              <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-purple-500 to-blue-500">
                <BookOpen className="h-4 w-4 text-white" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-white">Story Mode</h2>
                <p className="text-[11px] text-gray-500">Architecture Onboarding</p>
              </div>
            </div>
            {/* Progress bar */}
            <div className="mt-3">
              <div className="flex items-center justify-between text-[10px] text-gray-500 mb-1.5">
                <span>Progress</span>
                <span>{activeChapter + 1} / {chapters.length}</span>
              </div>
              <div className="h-1 w-full overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          </div>

          {/* Chapter list */}
          <nav className="flex-1 overflow-y-auto p-2">
            {chapters.map((ch, idx) => {
              const t = getTheme(idx);
              const isActive = idx === activeChapter;
              const isCompleted = idx < activeChapter;

              return (
                <button
                  key={idx}
                  onClick={() => goTo(idx)}
                  className={`group mb-1 flex w-full items-start gap-3 rounded-xl px-3 py-3 text-left transition-all duration-200 ${
                    isActive
                      ? "bg-white/[0.07] shadow-lg shadow-black/20"
                      : "hover:bg-white/[0.04]"
                  }`}
                >
                  {/* Number circle */}
                  <div
                    className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg text-xs font-bold transition-all ${
                      isActive
                        ? `${t.accentBg} ${t.accent} border ${t.accentBorder}`
                        : isCompleted
                        ? "bg-green-500/10 text-green-400 border border-green-500/20"
                        : "bg-white/5 text-gray-500 border border-white/10"
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    ) : (
                      <span>{idx + 1}</span>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div
                      className={`text-[13px] font-medium leading-tight transition-colors ${
                        isActive ? "text-white" : "text-gray-400 group-hover:text-gray-200"
                      }`}
                    >
                      {ch.title}
                    </div>
                    {isActive && (
                      <div className="mt-1 flex items-center gap-2 text-[10px] text-gray-500">
                        {ch.related_nodes.length > 0 && (
                          <span className={`${t.accentBg} ${t.accent} rounded px-1.5 py-0.5`}>
                            {ch.related_nodes.length} nodes
                          </span>
                        )}
                        {ch.related_flows.length > 0 && (
                          <span className="rounded bg-white/5 px-1.5 py-0.5 text-gray-400">
                            {ch.related_flows.length} flows
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  {isActive && (
                    <div
                      className="mt-1 h-2 w-2 shrink-0 rounded-full"
                      style={{ background: t.gradient }}
                    />
                  )}
                </button>
              );
            })}
          </nav>
        </aside>

        {/* ═══════════════════════ Center Panel: Chapter Content ═══════════════════════ */}
        <main className="relative flex min-w-0 flex-1 flex-col">
          {/* Repo Summary Banner */}
          <div className="border-b border-white/10 bg-gradient-to-r from-purple-500/5 via-transparent to-blue-500/5 px-6 py-3">
            <p className="text-sm text-gray-400 leading-relaxed">
              <span className="font-medium text-gray-300">Summary: </span>
              {story.repository_summary}
            </p>
          </div>

          {/* Chapter Content Area */}
          {chapter ? (
            <div className="flex-1 overflow-y-auto">
              <div className="mx-auto max-w-3xl px-6 py-10">
                {/* Chapter badge */}
                <div className="mb-6 flex items-center gap-3">
                  <div
                    className="grid h-10 w-10 place-items-center rounded-xl shadow-lg"
                    style={{ background: theme.gradient }}
                  >
                    {(() => {
                      const Icon = theme.icon;
                      return <Icon className="h-5 w-5 text-white" />;
                    })()}
                  </div>
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-widest text-gray-500">
                      Chapter {activeChapter + 1} of {chapters.length}
                    </p>
                    <h1 className="text-2xl font-bold text-white">{chapter.title}</h1>
                  </div>
                </div>

                {/* Content body */}
                <div className="prose-invert mb-10 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 sm:p-8">
                  <div className="whitespace-pre-wrap text-[15px] leading-relaxed text-gray-300">
                    {chapter.content}
                  </div>
                </div>

                {/* Mobile: Related section */}
                <div className="mb-10 space-y-4 lg:hidden">
                  {chapter.related_nodes.length > 0 && (
                    <div className={`rounded-xl border ${theme.accentBorder} ${theme.accentBg} p-4`}>
                      <h3 className={`mb-2 text-xs font-semibold uppercase tracking-wider ${theme.accent}`}>
                        Related Nodes
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {chapter.related_nodes.map((nid) => (
                          <button
                            key={nid}
                            onClick={() => navigateToGraph("node", nid)}
                            className="rounded-lg bg-black/30 px-2.5 py-1 text-xs font-mono text-gray-300 border border-white/10 hover:border-white/30"
                          >
                            {nid.length > 12 ? nid.slice(0, 12) + "…" : nid}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {chapter.related_flows.length > 0 && (
                    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-400">
                        Related Flows
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {chapter.related_flows.map((fid) => (
                          <button
                            key={fid}
                            onClick={() => navigateToGraph("flow", fid)}
                            className="rounded-lg bg-black/30 px-2.5 py-1 text-xs font-mono text-gray-300 border border-white/10 hover:border-white/30"
                          >
                            {fid}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Navigation buttons */}
                <div className="flex items-center justify-between">
                  <button
                    onClick={() => goTo(activeChapter - 1)}
                    disabled={activeChapter === 0}
                    className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-5 py-2.5 text-sm font-medium text-gray-300 transition-all hover:bg-white/[0.06] hover:text-white disabled:pointer-events-none disabled:opacity-30"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </button>
                  {activeChapter < chapters.length - 1 ? (
                    <button
                      onClick={() => goTo(activeChapter + 1)}
                      className="flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white transition-all hover:opacity-90 shadow-lg"
                      style={{ background: theme.gradient }}
                    >
                      Next Chapter
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  ) : (
                    <div className="flex items-center gap-2 rounded-xl bg-green-500/10 border border-green-500/20 px-5 py-2.5 text-sm font-medium text-green-400">
                      <CheckCircle2 className="h-4 w-4" />
                      Onboarding Complete
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-1 items-center justify-center text-gray-500">
              No chapters available.
            </div>
          )}
        </main>

        {/* ═══════════════════════ Right Panel: Graph References ═══════════════════════ */}
        <aside className="hidden w-72 shrink-0 flex-col border-l border-white/10 bg-[#0b0b0d] lg:flex">
          <div className="border-b border-white/10 p-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <ExternalLink className="h-3.5 w-3.5 text-gray-500" />
              Graph References
            </h3>
            <p className="mt-0.5 text-[11px] text-gray-500">
              Click to highlight in architecture view
            </p>
          </div>

          {chapter ? (
            <div className="flex-1 overflow-y-auto p-3 space-y-4">
              {/* Related Nodes */}
              <div>
                <div className={`mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider ${theme.accent}`}>
                  <div className="h-px flex-1 bg-white/5" />
                  <span>Nodes ({chapter.related_nodes.length})</span>
                  <div className="h-px flex-1 bg-white/5" />
                </div>
                {chapter.related_nodes.length > 0 ? (
                  <div className="space-y-1.5">
                    {chapter.related_nodes.map((nid) => (
                      <button
                        key={nid}
                        onClick={() => navigateToGraph("node", nid)}
                        className={`group flex w-full items-center gap-2 rounded-lg border ${theme.accentBorder} ${theme.accentBg} px-3 py-2 text-left transition-all hover:bg-opacity-20 hover:border-white/30`}
                      >
                        <div
                          className="h-2 w-2 shrink-0 rounded-full"
                          style={{ background: theme.gradient }}
                        />
                        <span className="min-w-0 truncate text-xs font-mono text-gray-300 group-hover:text-white">
                          {nid}
                        </span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="py-3 text-center text-[11px] text-gray-600">
                    No related nodes
                  </p>
                )}
              </div>

              {/* Related Flows */}
              <div>
                <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
                  <div className="h-px flex-1 bg-white/5" />
                  <span>Flows ({chapter.related_flows.length})</span>
                  <div className="h-px flex-1 bg-white/5" />
                </div>
                {chapter.related_flows.length > 0 ? (
                  <div className="space-y-1.5">
                    {chapter.related_flows.map((fid) => (
                      <button
                        key={fid}
                        onClick={() => navigateToGraph("flow", fid)}
                        className="group flex w-full items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-left transition-all hover:bg-white/[0.06]"
                      >
                        <Workflow className="h-3 w-3 shrink-0 text-gray-500 group-hover:text-purple-400" />
                        <span className="min-w-0 truncate text-xs font-mono text-gray-400 group-hover:text-white">
                          {fid}
                        </span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="py-3 text-center text-[11px] text-gray-600">
                    No related flows
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-1 items-center justify-center text-xs text-gray-600">
              Select a chapter
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
