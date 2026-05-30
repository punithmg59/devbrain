import { useEffect, useState } from "react";
import { Loader2, Sparkles, X } from "lucide-react";
import { getFile, summarizeNode } from "../services/repoDetailService";
import type { FileDetail, NodeResponse } from "../types/repo";
import LoadingSpinner from "./ui/LoadingSpinner";
import ErrorState from "./ErrorState";

interface FileDetailPanelProps {
  repoId: string;
  fileId: string;
  onClose: () => void;
}

function NodeTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    function: "bg-blue-900/40 text-blue-400 border-blue-700/40",
    class: "bg-purple-900/40 text-purple-400 border-purple-700/40",
    method: "bg-teal-900/40 text-teal-400 border-teal-700/40",
    api_route: "bg-green-900/40 text-green-400 border-green-700/40",
  };
  return (
    <span
      className={`px-1.5 py-0.5 text-[10px] font-medium rounded border ${
        colors[type] ?? "bg-gray-800 text-gray-400 border-gray-700"
      }`}
    >
      {type}
    </span>
  );
}

function SummarizeButton({
  repoId,
  node,
  onSummary,
}: {
  repoId: string;
  node: NodeResponse;
  onSummary: (summary: string, tags: string[]) => void;
}) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      const res = await summarizeNode(repoId, node.id);
      onSummary(res.summary, res.tags);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className="flex items-center gap-1 text-[11px] px-2 py-1 bg-purple-600/20 text-purple-400 border border-purple-700/30 rounded hover:bg-purple-600/30 disabled:opacity-50 transition-colors"
    >
      {loading ? (
        <Loader2 className="w-3 h-3 animate-spin" />
      ) : (
        <Sparkles className="w-3 h-3" />
      )}
      Summarize
    </button>
  );
}

export default function FileDetailPanel({ repoId, fileId, onClose }: FileDetailPanelProps) {
  const [data, setData] = useState<FileDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getFile(repoId, fileId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [repoId, fileId]);

  const handleNodeSummary = (nodeId: string, summary: string, tags: string[]) => {
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        nodes: prev.nodes.map((n) =>
          n.id === nodeId ? { ...n, summary, tags } : n
        ),
      };
    });
  };

  if (loading) return <LoadingSpinner text="Loading file..." />;
  if (error) return <ErrorState message={error} retry={() => { setLoading(true); setError(null); getFile(repoId, fileId).then(setData).catch((e) => setError(e.message)).finally(() => setLoading(false)); }} />;
  if (!data) return null;

  const { file, nodes } = data;

  return (
    <div className="animate-in fade-in slide-in-from-top-2 duration-200">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0">
          <p className="text-sm font-mono text-gray-300 break-all">{file.file_path}</p>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
            <span>{file.line_count.toLocaleString()} lines</span>
            <span>{file.size_bytes.toLocaleString()} bytes</span>
            {file.language && (
              <span className="px-1.5 py-0.5 bg-gray-800 rounded text-gray-400">
                {file.language}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-gray-500 hover:text-gray-300 transition-colors shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content preview */}
      {file.content_preview && (
        <div className="mb-6">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Preview
          </p>
          <pre className="bg-[#0a0a0a] border border-gray-800 rounded-lg p-4 text-xs font-mono text-gray-300 max-h-[200px] overflow-auto leading-relaxed">
            {file.content_preview}
          </pre>
        </div>
      )}

      {/* Functions in file */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Functions &amp; Classes ({nodes.length})
        </p>
        {nodes.length === 0 ? (
          <p className="text-sm text-gray-600 italic">No functions found in this file</p>
        ) : (
          <div className="space-y-2">
            {nodes.map((node) => (
              <div
                key={node.id}
                className="p-3 bg-gray-900/50 border border-gray-800 rounded-lg hover:border-gray-700 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm text-gray-200">{node.name}</span>
                  <NodeTypeBadge type={node.node_type} />
                  {node.is_async && (
                    <span className="px-1.5 py-0.5 text-[10px] bg-yellow-900/30 text-yellow-400 border border-yellow-700/30 rounded">
                      async
                    </span>
                  )}
                </div>
                {node.start_line != null && node.end_line != null && (
                  <p className="text-[11px] text-gray-600 mb-1">
                    Lines {node.start_line} – {node.end_line}
                  </p>
                )}
                {node.signature && (
                  <p className="text-[11px] font-mono text-gray-500 truncate mb-1">
                    {node.signature}
                  </p>
                )}
                {node.summary ? (
                  <div>
                    <p className="text-xs text-gray-400 italic">{node.summary}</p>
                    {node.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {node.tags.map((tag) => (
                          <span
                            key={tag}
                            className="px-1.5 py-0.5 text-[10px] bg-gray-800 text-gray-400 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="mt-1">
                    <SummarizeButton
                      repoId={repoId}
                      node={node}
                      onSummary={(summary, tags) => handleNodeSummary(node.id, summary, tags)}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
