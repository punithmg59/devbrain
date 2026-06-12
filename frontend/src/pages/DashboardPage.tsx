import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { GitBranch, Loader2, Play, RefreshCw, Zap } from "lucide-react";
import useAuthStore from "../hooks/useAuthStore";
import ConnectRepoModal from "../components/ConnectRepoModal";
import { ConnectedRepo, repoService } from "../services/repoService";

const ACTIVE_STATUSES = new Set(["queued", "analyzing"]);

function statusStyle(status: string): string {
  switch (status) {
    case "completed":
      return "bg-green-900/30 text-green-400";
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
  const [repos, setRepos] = useState<ConnectedRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [analyzingIds, setAnalyzingIds] = useState<Set<string>>(new Set());
  const reposRef = useRef(repos);
  reposRef.current = repos;

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
                    repo.analysis_status === "completed");

                return (
                  <li
                    key={repo.id}
                    className="p-4 bg-gray-900/50 border border-gray-800 rounded-xl flex items-center justify-between gap-4"
                  >
                    <div className="min-w-0">
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
                        {repo.analysis_status === "completed" && (
                          <span className="text-gray-500">
                            {repo.total_files} files · {repo.total_functions} functions ·{" "}
                            {repo.total_lines.toLocaleString()} lines
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                      {repo.analysis_status === "completed" && (
                        <>
                          <Link
                            to={`/repos/${repo.id}`}
                            className="px-3 py-1.5 text-sm border border-gray-600 hover:border-gray-500 rounded-lg transition-colors"
                          >
                            View Details
                          </Link>
                          <Link
                            to={`/repos/${repo.id}/impact`}
                            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-purple-600 text-purple-400 hover:bg-purple-900/30 rounded-lg transition-colors"
                          >
                            <Zap className="w-3.5 h-3.5" />
                            Impact Radar
                          </Link>
                        </>
                      )}
                      {canAnalyze && (
                        <button
                          onClick={() => handleAnalyze(repo.id)}
                          disabled={analyzingIds.has(repo.id)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-purple-600 hover:bg-purple-500 disabled:opacity-50 rounded-lg transition-colors"
                        >
                          {repo.analysis_status === "completed" ? (
                            <>
                              <RefreshCw className="w-3.5 h-3.5" />
                              Re-analyze
                            </>
                          ) : (
                            <>
                              <Play className="w-3.5 h-3.5" />
                              Analyze
                            </>
                          )}
                        </button>
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
    </div>
  );
}
