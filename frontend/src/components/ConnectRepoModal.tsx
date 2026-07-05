import { useEffect, useState } from "react";
import { Github, Loader2, Search, X } from "lucide-react";
import { GitHubRepoItem, repoService } from "../services/repoService";

interface ConnectRepoModalProps {
  open: boolean;
  onClose: () => void;
  onConnected: () => void;
}

export default function ConnectRepoModal({ open, onClose, onConnected }: ConnectRepoModalProps) {
  const [repos, setRepos] = useState<GitHubRepoItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [connecting, setConnecting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    setRepos([]);
    repoService
      .listAvailable()
      .then(setRepos)
      .catch((err) => {
        const msg = err.response?.data?.detail ?? "Failed to load repositories";
        setError(typeof msg === "string" ? msg : "Failed to load repositories");
      })
      .finally(() => setLoading(false));
  }, [open]);

  const filtered = repos.filter(
    (r) =>
      r.full_name.toLowerCase().includes(search.toLowerCase()) ||
      (r.description ?? "").toLowerCase().includes(search.toLowerCase())
  );

  const handleConnect = async (repo: GitHubRepoItem) => {
    if (repo.already_connected) return;
    setConnecting(repo.github_repo_id);
    setError(null);
    try {
      await repoService.connect(repo.github_repo_id);
      onConnected();
      onClose();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail ?? "Failed to connect repository");
    } finally {
      setConnecting(null);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative w-full max-w-lg bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Github className="w-5 h-5" />
            Connect Repository
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-3 border-b border-gray-800">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search repositories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-purple-500"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {error && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-sm text-red-300">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
            </div>
          ) : filtered.length === 0 ? (
            <p className="text-center text-gray-500 py-12">No repositories found</p>
          ) : (
            <ul className="space-y-2">
              {filtered.map((repo) => (
                <li
                  key={repo.github_repo_id}
                  className="flex items-center justify-between p-3 bg-gray-800/50 border border-gray-700 rounded-lg hover:border-gray-600"
                >
                  <div className="min-w-0 flex-1 mr-3">
                    <p className="font-medium truncate">{repo.full_name}</p>
                    {repo.description && (
                      <p className="text-xs text-gray-500 truncate">{repo.description}</p>
                    )}
                    <div className="flex gap-2 mt-1">
                      {repo.language && (
                        <span className="text-xs text-gray-400">{repo.language}</span>
                      )}
                      {repo.is_private && (
                        <span className="text-xs text-yellow-500">Private</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleConnect(repo)}
                    disabled={repo.already_connected || connecting === repo.github_repo_id}
                    className="shrink-0 px-3 py-1.5 text-sm rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed bg-purple-600 hover:bg-purple-500 disabled:bg-gray-600"
                  >
                    {connecting === repo.github_repo_id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : repo.already_connected ? (
                      "Connected"
                    ) : (
                      "Connect"
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
