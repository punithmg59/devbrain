import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  GitBranch,
  Loader2,
  MoreVertical,
  Trash2,
  ChevronRight,
  Zap,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  Clock,
} from "lucide-react";
import useAuthStore from "../hooks/useAuthStore";
import ConnectRepoModal from "../components/ConnectRepoModal";
import DeleteRepoModal from "../components/DeleteRepoModal";
import { ConnectedRepo, repoService, AnalysisProgressResponse } from "../services/repoService";
import { isAnalyzed } from "../types/repo";
import { useToast } from "../components/Toast";

const ACTIVE_STATUSES = new Set([
  "queued",
  "cloning",
  "scanning",
  "parsing",
  "building_graph",
  "saving",
  "analyzing",
]);

interface ProgressState {
  progress_percent: number;
  current_stage: string;
  status: string;
}

function formatStatusLabel(status?: string, stage?: string): string {
  const s = status || "pending";
  if (s === "building_graph" || stage === "building_graph") return "Building Graph";
  if (s === "completed_with_warnings") return "Completed (Warnings)";
  if (s === "completed") return "Completed";
  if (s === "failed") return "Failed";
  if (s === "pending") return "Pending";
  if (s === "queued") return "Queued";
  if (s === "cloning") return "Cloning";
  if (s === "scanning") return "Scanning";
  if (s === "parsing") return "Parsing";
  if (s === "saving") return "Saving";
  if (s === "analyzing") return "Analyzing";
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function statusStyle(status?: string): string {
  const s = status || "pending";
  switch (s) {
    case "completed":
      return "bg-green-900/30 text-green-400 border border-green-700/30";
    case "completed_with_warnings":
      return "bg-amber-900/30 text-amber-400 border border-amber-700/30";
    case "analyzing":
    case "queued":
    case "cloning":
    case "scanning":
    case "parsing":
    case "building_graph":
    case "saving":
      return "bg-blue-900/30 text-blue-400 border border-blue-700/30";
    case "failed":
      return "bg-red-900/30 text-red-400 border border-red-700/30";
    case "pending":
      return "bg-amber-900/20 text-amber-400 border border-amber-600/30";
    default:
      return "bg-gray-800 text-gray-400 border border-gray-700/30";
  }
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [modalOpen, setModalOpen] = useState(false);
  const [deleteModalRepo, setDeleteModalRepo] = useState<ConnectedRepo | null>(null);
  const [repos, setRepos] = useState<ConnectedRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [analyzingIds, setAnalyzingIds] = useState<Set<string>>(new Set());
  const [progressMap, setProgressMap] = useState<Record<string, ProgressState>>({});
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  const reposRef = useRef(repos);
  reposRef.current = repos;
  const { addToast } = useToast();

  const loadRepos = useCallback(async () => {
    setLoadingRepos(true);
    try {
      console.log("[DASHBOARD] Fetching connected repositories...");
      const data = await repoService.listConnected();
      const safeData = Array.isArray(data) ? data : [];
      setRepos(safeData);
      console.log(`[DASHBOARD] Loaded ${safeData.length} repositories`);

      // Initialize progress for all repositories
      const initialProgress: Record<string, ProgressState> = {};
      for (const r of safeData) {
        if (isAnalyzed(r.analysis_status)) {
          initialProgress[r.id] = {
            progress_percent: 100,
            current_stage: r.analysis_status,
            status: r.analysis_status,
          };
        } else if (r.analysis_status === "pending") {
          initialProgress[r.id] = {
            progress_percent: 0,
            current_stage: "pending",
            status: "pending",
          };
        } else if (r.analysis_status === "failed") {
          initialProgress[r.id] = {
            progress_percent: 100,
            current_stage: "failed",
            status: "failed",
          };
        }
      }
      setProgressMap((prev) => ({ ...initialProgress, ...prev }));

      // For any currently active jobs, immediately fetch their real backend progress
      const activeRepos = safeData.filter((r) => ACTIVE_STATUSES.has(r.analysis_status));
      if (activeRepos.length > 0) {
        await Promise.all(
          activeRepos.map(async (r) => {
            try {
              const p = await repoService.getAnalysisProgress(r.id);
              if (p && typeof p.progress_percent === "number") {
                setProgressMap((prev) => ({
                  ...prev,
                  [r.id]: {
                    progress_percent: p.progress_percent,
                    current_stage: p.current_stage || r.analysis_status,
                    status: p.status || r.analysis_status,
                  },
                }));
              }
            } catch (fetchErr) {
              console.warn(`[DASHBOARD] Initial progress fetch failed for ${r.id}:`, fetchErr);
            }
          })
        );
      }
    } catch (err) {
      console.error("[DASHBOARD] Failed to load repositories:", err);
      setRepos([]);
    } finally {
      setLoadingRepos(false);
    }
  }, []);

  useEffect(() => {
    console.log(`[DASHBOARD] Dashboard mounted for user: ${user?.username || "unknown"}`);
    loadRepos();
  }, [loadRepos, user?.username]);

  useEffect(() => {
    const handleClickOutside = () => setMenuOpenId(null);
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  const hasActiveAnalysis = repos.some(
    (r) => ACTIVE_STATUSES.has(r.analysis_status) || analyzingIds.has(r.id)
  );

  // Polling loop for active analysis jobs
  useEffect(() => {
    if (!hasActiveAnalysis) return;

    const poll = async () => {
      const active = reposRef.current.filter(
        (r) => ACTIVE_STATUSES.has(r.analysis_status) || analyzingIds.has(r.id)
      );
      if (active.length === 0) return;

      console.log(`[DASHBOARD] Polling ${active.length} active repositories...`);

      const results = await Promise.all(
        active.map(async (repo) => {
          try {
            const p: AnalysisProgressResponse = await repoService.getAnalysisProgress(repo.id);
            if (p && typeof p.progress_percent === "number") {
              console.log(
                `[ANALYSIS_UI] progress repo_id=${repo.id} stage=${p.current_stage} progress=${p.progress_percent}% status=${p.status}`
              );
              return { repoId: repo.id, progress: p };
            }
            return null;
          } catch (err) {
            console.error(`[ANALYSIS_UI] polling_error repo_id=${repo.id}:`, err);
            return null;
          }
        })
      );

      // Update progressMap with real backend data
      setProgressMap((prev) => {
        const next = { ...prev };
        for (const item of results) {
          if (!item) continue;
          next[item.repoId] = {
            progress_percent: item.progress.progress_percent,
            current_stage: item.progress.current_stage || "analyzing",
            status: item.progress.status || "analyzing",
          };
        }
        return next;
      });

      // Update repo status in repo list
      setRepos((prev) =>
        prev.map((repo) => {
          const match = results.find((r) => r?.repoId === repo.id);
          if (!match) return repo;
          const { progress } = match;

          const isTerminal =
            progress.status === "completed" ||
            progress.status === "completed_with_warnings" ||
            progress.status === "failed";

          if (isTerminal) {
            if (progress.status === "completed" || progress.status === "completed_with_warnings") {
              console.log(`[ANALYSIS_UI] analysis_completed repo_id=${repo.id}`);
            } else {
              console.log(`[ANALYSIS_UI] analysis_failed repo_id=${repo.id}`);
            }
          }

          return {
            ...repo,
            analysis_status: progress.status || repo.analysis_status,
            has_completed_analysis: (progress.status === "completed" || progress.status === "completed_with_warnings") ? true : repo.has_completed_analysis,
            total_files: progress.files_total || repo.total_files || 0,
            total_functions: progress.functions_found || repo.total_functions || 0,
          };
        })
      );

      // Clean up finished analyzing IDs
      for (const item of results) {
        if (!item) continue;
        const s = item.progress.status;
        if (s === "completed" || s === "completed_with_warnings" || s === "failed") {
          setAnalyzingIds((prev) => {
            const next = new Set(prev);
            next.delete(item.repoId);
            return next;
          });
        }
      }
    };

    poll();
    const timer = setInterval(poll, 1500);
    return () => clearInterval(timer);
  }, [hasActiveAnalysis, analyzingIds]);

  const handleAnalyze = async (repoId: string) => {
    console.log(`[ANALYSIS_UI] reanalysis_clicked repo_id=${repoId}`);
    setAnalyzingIds((prev) => new Set(prev).add(repoId));

    // Reset progress to 0% for this repo immediately
    setProgressMap((prev) => ({
      ...prev,
      [repoId]: {
        progress_percent: 0,
        current_stage: "queued",
        status: "queued",
      },
    }));

    addToast("Starting repository analysis...", "info", 3000);
    try {
      console.log(`[ANALYSIS_UI] starting_analysis repo_id=${repoId}`);
      const res = await repoService.analyze(repoId);
      console.log(`[ANALYSIS_UI] analysis_started job_id=${res?.job_id || "ok"}`);

      setRepos((prev) =>
        prev.map((r) =>
          r.id === repoId ? { ...r, analysis_status: "queued" } : r
        )
      );
      addToast("Analysis queued successfully", "success", 3000);
    } catch (err) {
      console.error(`[ANALYSIS_UI] analysis_failed repo_id=${repoId} error=`, err);
      // Revert analyzing state on failure
      setAnalyzingIds((prev) => {
        const next = new Set(prev);
        next.delete(repoId);
        return next;
      });
      addToast("Failed to start analysis", "error");
    }
  };

  const handleDeleteRepo = async (repoId: string) => {
    const previousRepos = reposRef.current;
    setRepos((prev) => prev.filter((r) => r.id !== repoId));
    addToast("Deleting...", "info", 2000);

    try {
      await repoService.disconnect(repoId);
      addToast("Repository deleted successfully", "success");
    } catch (err) {
      console.error("[DASHBOARD] Delete repository failed:", err);
      setRepos(previousRepos);
      addToast("Failed to delete repository", "error");
    }
  };

  // Safe fallback if user object is not yet available
  if (!user) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex flex-col items-center justify-center gap-3 text-white">
        <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
        <p className="text-xs text-gray-400 font-mono">Loading dashboard...</p>
      </div>
    );
  }

  const username = user.username || "Developer";
  const userPlan = user.plan || "FREE";

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white">
      {/* Top navigation */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <span className="text-xl font-bold tracking-tight">DevBrain</span>
        <div className="flex items-center gap-4">
          {user.avatar_url && (
            <img
              src={user.avatar_url}
              alt={username}
              className="w-8 h-8 rounded-full"
            />
          )}
          <span className="text-sm text-gray-300 font-medium">{username}</span>
          <button
            onClick={() => logout()}
            className="text-sm px-3 py-1.5 border border-gray-700 rounded-lg hover:border-gray-500 transition-colors"
          >
            Logout
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-12">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold">Welcome back, {username}</h1>
          <span className="px-2 py-0.5 text-xs font-medium bg-purple-600/20 text-purple-400 rounded border border-purple-500/30">
            {userPlan}
          </span>
        </div>
        <p className="text-gray-400 mb-10">Your AI engineering intelligence dashboard</p>

        {loadingRepos ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
          </div>
        ) : repos.length === 0 ? (
          <div className="p-8 bg-gray-900/50 border border-gray-800 rounded-xl">
            <h2 className="text-xl font-semibold mb-2">Connect Your First Repository</h2>
            <p className="text-gray-400 mb-6">
              Connect a GitHub repository to start analyzing your codebase with AI
            </p>
            <button
              onClick={() => setModalOpen(true)}
              className="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 rounded-lg font-medium transition-colors"
            >
              Connect Repository
            </button>
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Your Repositories</h2>
              <button
                onClick={() => setModalOpen(true)}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium transition-colors"
              >
                + Connect Repository
              </button>
            </div>

            <ul className="space-y-3.5">
              {repos.map((repo) => {
                const repoStatus = repo.analysis_status || "pending";
                const isRunning =
                  ACTIVE_STATUSES.has(repoStatus) ||
                  analyzingIds.has(repo.id);

                // Real progress from backend state
                const prog = progressMap[repo.id];
                let currentProgress = 0;
                if (prog && typeof prog.progress_percent === "number") {
                  currentProgress = prog.progress_percent;
                } else if (isAnalyzed(repoStatus)) {
                  currentProgress = 100;
                } else if (repoStatus === "failed") {
                  currentProgress = 100;
                }

                const isMenuOpen = menuOpenId === repo.id;

                return (
                  <li
                    key={repo.id}
                    className="p-5 bg-[#121214] border border-gray-800/80 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-5 relative shadow-sm hover:border-gray-700/80 transition-all group"
                  >
                    {/* Left side: Repository info, meta, status badge, re-analysis & explore buttons */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        {isAnalyzed(repoStatus) ? (
                          <Link
                            to={`/repos/${repo.id}`}
                            className="font-semibold text-base text-white hover:text-purple-300 transition-colors truncate"
                          >
                            {repo.full_name || repo.name || "Repository"}
                          </Link>
                        ) : (
                          <span className="font-semibold text-base text-white truncate">
                            {repo.full_name || repo.name || "Repository"}
                          </span>
                        )}
                      </div>

                      {repo.description && (
                        <p className="text-sm text-gray-400 mt-1 truncate max-w-xl">
                          {repo.description}
                        </p>
                      )}

                      {/* Meta attributes & Action buttons row */}
                      <div className="flex flex-wrap items-center gap-2.5 sm:gap-3 mt-3 text-xs text-gray-400">
                        {/* Branch */}
                        <span className="flex items-center gap-1.5 font-mono text-gray-400">
                          <GitBranch className="w-3.5 h-3.5 text-gray-500 shrink-0" />
                          {repo.default_branch || "main"}
                        </span>

                        {/* Language */}
                        {repo.language && (
                          <span className="font-medium text-gray-400">{repo.language}</span>
                        )}

                        {/* Status Badge */}
                        <span
                          className={`px-2.5 py-0.5 rounded-md capitalize text-xs font-medium flex items-center gap-1.5 ${statusStyle(
                            repoStatus
                          )}`}
                        >
                          {isRunning ? (
                            <RotateCw className="w-3 h-3 animate-spin shrink-0 text-blue-400" />
                          ) : repoStatus === "completed" || repoStatus === "completed_with_warnings" ? (
                            <CheckCircle2 className="w-3 h-3 text-green-400 shrink-0" />
                          ) : repoStatus === "failed" ? (
                            <AlertCircle className="w-3 h-3 text-red-400 shrink-0" />
                          ) : (
                            <Clock className="w-3 h-3 text-amber-400 shrink-0" />
                          )}
                          {formatStatusLabel(repoStatus, prog?.current_stage)}
                        </span>

                        {/* Re-analysis / Analyze Button */}
                        {!isRunning && (
                          <button
                            onClick={() => handleAnalyze(repo.id)}
                            disabled={analyzingIds.has(repo.id)}
                            className="px-2.5 py-0.5 text-xs font-medium border border-gray-700 hover:border-gray-500 rounded text-gray-200 hover:text-white bg-transparent hover:bg-white/5 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                            title="Trigger repository analysis"
                          >
                            {analyzingIds.has(repo.id) ? (
                              <>
                                <Loader2 className="w-3 h-3 animate-spin text-purple-400 shrink-0" />
                                <span>Analyzing...</span>
                              </>
                            ) : repo.has_completed_analysis ? (
                              <span>Re-analyze</span>
                            ) : (
                              <span>Analyze</span>
                            )}
                          </button>
                        )}

                        {/* Explore Repository Button (beside Re-analyze) */}
                        {!isRunning && isAnalyzed(repoStatus) && (
                          <Link
                            to={`/repos/${repo.id}`}
                            className="px-2.5 py-0.5 text-xs font-medium border border-purple-600/40 hover:border-purple-500 rounded text-purple-300 hover:text-white bg-purple-950/20 hover:bg-purple-900/30 transition-all flex items-center gap-1"
                            title="Explore repository details"
                          >
                            <span>Explore Repository</span>
                            <ChevronRight className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                          </Link>
                        )}
                      </div>
                    </div>

                    {/* Right side: Real-time Progress Bar, Percentage & Menu */}
                    <div className="flex items-center gap-4 shrink-0 w-full md:w-auto justify-between md:justify-end">
                      {/* Real Progress Bar & Percentage */}
                      <div className="flex items-center gap-3 w-full md:w-auto">
                        <div
                          className="relative w-full md:w-56 lg:w-72 h-3.5 bg-gray-950/80 border border-gray-700/80 rounded-full overflow-hidden shadow-inner flex items-center"
                          title={`Analysis Progress: ${Math.round(currentProgress)}% (${formatStatusLabel(
                            repoStatus,
                            prog?.current_stage
                          )})`}
                        >
                          <div
                            className={`h-full rounded-full transition-all duration-500 ease-out ${
                              repoStatus === "failed"
                                ? "bg-red-500"
                                : isRunning
                                ? "bg-gradient-to-r from-emerald-500 via-green-400 to-emerald-400 progress-striped"
                                : isAnalyzed(repoStatus)
                                ? "bg-emerald-500"
                                : "bg-gray-800"
                            }`}
                            style={{
                              width: `${Math.min(100, Math.max(0, currentProgress))}%`,
                            }}
                          />
                        </div>

                        {/* Percentage Label */}
                        <span className="text-sm font-semibold italic text-gray-200 min-w-[2.5rem] text-right font-mono">
                          {Math.round(currentProgress)}%
                        </span>
                      </div>

                      {/* Three-dot Kebab Menu (Impact Radar, Delete Repository) */}
                      <div className="relative">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setMenuOpenId(isMenuOpen ? null : repo.id);
                          }}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
                          aria-label="Actions menu"
                        >
                          <MoreVertical className="w-5 h-5" />
                        </button>

                        {isMenuOpen && (
                          <div
                            className="absolute right-0 top-full mt-2 w-52 bg-gray-900 border border-gray-800 rounded-xl shadow-2xl z-20 overflow-hidden"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <div className="py-1">
                              {/* Impact Radar (only if analyzed) */}
                              {isAnalyzed(repoStatus) && (
                                <>
                                  <Link
                                    to={`/repos/${repo.id}/impact`}
                                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-left text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                                    onClick={() => setMenuOpenId(null)}
                                  >
                                    <Zap className="w-4 h-4 text-yellow-400" />
                                    Impact Radar
                                  </Link>

                                  <div className="h-px bg-gray-800 my-1" />
                                </>
                              )}

                              {/* Delete Repository */}
                              <button
                                onClick={() => {
                                  setDeleteModalRepo(repo);
                                  setMenuOpenId(null);
                                }}
                                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-left text-red-400 hover:bg-red-950/50 hover:text-red-300 transition-colors"
                              >
                                <Trash2 className="w-4 h-4" />
                                Delete Repository
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </main>

      <ConnectRepoModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onConnected={loadRepos}
      />

      <DeleteRepoModal
        repo={deleteModalRepo}
        open={!!deleteModalRepo}
        onClose={() => setDeleteModalRepo(null)}
        onConfirm={handleDeleteRepo}
      />
    </div>
  );
}
