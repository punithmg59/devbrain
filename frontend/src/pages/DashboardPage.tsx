import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { GitBranch, Loader2, Play, RefreshCw, Zap, MoreVertical, Trash2, ChevronRight } from "lucide-react";
import useAuthStore from "../hooks/useAuthStore";
import ConnectRepoModal from "../components/ConnectRepoModal";
import DeleteRepoModal from "../components/DeleteRepoModal";
import { ConnectedRepo, repoService } from "../services/repoService";
import { isAnalyzed } from "../types/repo";
import { useToast } from "../components/Toast";

const ACTIVE_STATUSES = new Set(["queued", "analyzing"]);

function statusStyle(status: string): string {
  switch (status) {
    case "completed":
      return "bg-green-900/30 text-green-400";
    case "completed_with_warnings":
      return "bg-amber-900/30 text-amber-400";
    case "analyzing":
    case "queued":
      return "bg-blue-900/30 text-blue-400";
    case "failed":
      return "bg-red-900/30 text-red-400";
    default:
      return "bg-yellow-900/30 text-yellow-400";
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
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  
  const reposRef = useRef(repos);
  reposRef.current = repos;
  const { addToast } = useToast();

  const loadRepos = useCallback(async () => {
    setLoadingRepos(true);
    try {
      const data = await repoService.listConnected();
      setRepos(data);
    } catch {
      setRepos([]);
    } finally {
      setLoadingRepos(false);
    }
  }, []);

  useEffect(() => {
    loadRepos();
  }, [loadRepos]);

  useEffect(() => {
    const handleClickOutside = () => setMenuOpenId(null);
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  const hasActiveAnalysis = repos.some((r) => ACTIVE_STATUSES.has(r.analysis_status));

  useEffect(() => {
    if (!hasActiveAnalysis) return;

    const poll = async () => {
      const active = reposRef.current.filter((r) =>
        ACTIVE_STATUSES.has(r.analysis_status)
      );
      if (active.length === 0) return;

      const updates = await Promise.all(
        active.map(async (repo) => {
          try {
            const status = await repoService.getAnalysisStatus(repo.id);
            return { id: repo.id, ...status };
          } catch {
            return null;
          }
        })
      );

      setRepos((prev) =>
        prev.map((repo) => {
          const update = updates.find((u) => u?.id === repo.id);
          if (!update) return repo;
          return {
            ...repo,
            analysis_status: update.analysis_status,
            total_files: update.total_files,
            total_functions: update.total_functions,
            total_lines: update.total_lines,
          };
        })
      );
    };

    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, [hasActiveAnalysis]);

  const handleAnalyze = async (repoId: string) => {
    setAnalyzingIds((prev) => new Set(prev).add(repoId));
    try {
      await repoService.analyze(repoId);
      setRepos((prev) =>
        prev.map((r) =>
          r.id === repoId ? { ...r, analysis_status: "queued" } : r
        )
      );
    } catch {
      // keep UI unchanged on error
    } finally {
      setAnalyzingIds((prev) => {
        const next = new Set(prev);
        next.delete(repoId);
        return next;
      });
    }
  };

  const handleDeleteRepo = async (repoId: string) => {
    // Optimistic update
    const previousRepos = reposRef.current;
    setRepos((prev) => prev.filter((r) => r.id !== repoId));
    addToast("Deleting...", "info", 2000);
    
    try {
      await repoService.disconnect(repoId);
      addToast("Repository deleted successfully", "success");
    } catch (e) {
      setRepos(previousRepos);
      addToast("Failed to delete repository", "error");
    }
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <span className="text-xl font-bold">DevBrain</span>
        <div className="flex items-center gap-4">
          {user.avatar_url && (
            <img
              src={user.avatar_url}
              alt={user.username}
              className="w-8 h-8 rounded-full"
            />
          )}
          <span className="text-sm text-gray-300">{user.username}</span>
          <button
            onClick={() => logout()}
            className="text-sm px-3 py-1.5 border border-gray-600 rounded-lg hover:border-gray-500 transition-colors"
          >
            Logout
          </button>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-12">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold">Welcome back, {user.username}</h1>
          <span className="px-2 py-0.5 text-xs font-medium bg-purple-600/20 text-purple-400 rounded border border-purple-500/30">
            {user.plan}
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
            <ul className="space-y-3">
              {repos.map((repo) => {
                const isRunning =
                  ACTIVE_STATUSES.has(repo.analysis_status) ||
                  analyzingIds.has(repo.id);
                const canAnalyze =
                  !isRunning &&
                  (repo.analysis_status === "pending" ||
                    repo.analysis_status === "failed" ||
                    isAnalyzed(repo.analysis_status));
                const isMenuOpen = menuOpenId === repo.id;

                return (
                  <li
                    key={repo.id}
                    className="p-4 bg-gray-900/50 border border-gray-800 rounded-xl flex items-center justify-between gap-4 relative"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{repo.full_name}</p>
                      {repo.description && (
                        <p className="text-sm text-gray-500 mt-1 truncate">
                          {repo.description}
                        </p>
                      )}
                      <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-gray-400">
                        <span className="flex items-center gap-1">
                          <GitBranch className="w-3 h-3" />
                          {repo.default_branch}
                        </span>
                        {repo.language && <span>{repo.language}</span>}
                        <span
                          className={`px-1.5 py-0.5 rounded capitalize ${statusStyle(repo.analysis_status)}`}
                        >
                          {isRunning && (
                            <Loader2 className="inline w-3 h-3 mr-1 animate-spin" />
                          )}
                          {repo.analysis_status}
                        </span>
                        {isAnalyzed(repo.analysis_status) && (
                          <span className="text-gray-500">
                            {repo.total_files} files · {repo.total_functions} functions ·{" "}
                            {repo.total_lines.toLocaleString()} lines
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 relative">
                      {isAnalyzed(repo.analysis_status) && (
                        <>
                          <Link
                            to={`/repos/${repo.id}/impact`}
                            className="hidden sm:flex items-center gap-1 px-3 py-1.5 text-sm border border-purple-600 text-purple-400 hover:bg-purple-900/30 rounded-lg transition-colors"
                          >
                            <Zap className="w-3.5 h-3.5" />
                            Impact Radar
                          </Link>
                          <Link
                            to={`/repos/${repo.id}`}
                            className="hidden sm:flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg transition-colors"
                          >
                            Explore
                            <ChevronRight className="w-4 h-4" />
                          </Link>
                        </>
                      )}
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setMenuOpenId(isMenuOpen ? null : repo.id);
                        }}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors ml-1"
                      >
                        <MoreVertical className="w-5 h-5" />
                      </button>

                      {isMenuOpen && (
                        <div 
                          className="absolute right-0 top-full mt-2 w-48 bg-gray-900 border border-gray-800 rounded-xl shadow-xl z-10 overflow-hidden"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div className="py-1">
                            {canAnalyze && (
                              <button
                                onClick={() => {
                                  handleAnalyze(repo.id);
                                  setMenuOpenId(null);
                                }}
                                disabled={analyzingIds.has(repo.id)}
                                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-left text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                              >
                                {isAnalyzed(repo.analysis_status) ? (
                                  <>
                                    <RefreshCw className="w-4 h-4" />
                                    Re-analyze
                                  </>
                                ) : (
                                  <>
                                    <Play className="w-4 h-4" />
                                    Analyze
                                  </>
                                )}
                              </button>
                            )}
                            {isAnalyzed(repo.analysis_status) && (
                              <Link
                                to={`/repos/${repo.id}`}
                                className="w-full sm:hidden flex items-center gap-2 px-4 py-2 text-sm text-left text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                              >
                                <ChevronRight className="w-4 h-4" />
                                View Details
                              </Link>
                            )}
                            <div className="h-px bg-gray-800 my-1" />
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
