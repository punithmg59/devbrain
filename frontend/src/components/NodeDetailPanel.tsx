import { useEffect, useState } from "react";
import { ArrowRight, Loader2, Sparkles, X } from "lucide-react";
import { getNode, summarizeNode } from "../services/repoDetailService";
import type { NodeDetail, NodeRelation } from "../types/repo";
import LoadingSpinner from "./ui/LoadingSpinner";

interface NodeDetailPanelProps {
  repoId: string;
  nodeId: string;
  onClose: () => void;
  onSelectNode?: (nodeId: string) => void;
  onSelectFile?: (fileId: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
  function: "bg-blue-900/40 text-blue-400 border-blue-700/40",
  class: "bg-purple-900/40 text-purple-400 border-purple-700/40",
  method: "bg-teal-900/40 text-teal-400 border-teal-700/40",
  api_route: "bg-green-900/40 text-green-400 border-green-700/40",
};

function highlightCode(code: string): React.ReactNode {
  // Simple keyword highlighting — no external library
  const keywords = new Set([
    "def", "class", "return", "if", "else", "elif", "for", "while", "import",
    "from", "async", "await", "try", "except", "finally", "with", "as", "yield",
    "raise", "pass", "break", "continue", "lambda", "not", "and", "or", "in",
    "is", "True", "False", "None",
    // JS/TS
    "function", "const", "let", "var", "export", "default", "interface", "type",
    "extends", "implements", "new", "this", "super", "throw", "catch",
  ]);

  return code.split("\n").map((line, i) => (
    <div key={i} className="flex">
      <span className="select-none text-gray-700 w-10 text-right pr-3 shrink-0">
        {i + 1}
      </span>
      <span>
        {line.split(/(\b\w+\b)/).map((token, j) =>
          keywords.has(token) ? (
            <span key={j} className="text-purple-400 font-medium">
              {token}
            </span>
          ) : /^"[^"]*"$|^'[^']*'$/.test(token) ? (
            <span key={j} className="text-green-400">
              {token}
            </span>
          ) : (
            <span key={j}>{token}</span>
          )
        )}
      </span>
    </div>
  ));
}

function RelationList({
  label,
  items,
  onSelect,
}: {
  label: string;
  items: NodeRelation[];
  onSelect?: (id: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mt-4">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
        {label} ({items.length})
      </p>
      <div className="space-y-1">
        {items.map((item) => (
          <button
            key={item.node_id}
            onClick={() => onSelect?.(item.node_id)}
            className="w-full text-left flex items-center gap-2 px-3 py-2 bg-gray-900/50 border border-gray-800 rounded-lg hover:border-purple-700/50 hover:bg-gray-800/50 transition-colors group"
          >
            <ArrowRight className="w-3 h-3 text-gray-600 group-hover:text-purple-400 transition-colors shrink-0" />
            <div className="min-w-0">
              <span className="text-sm text-gray-300 font-medium">{item.name}</span>
              <span className="ml-2 text-[10px] text-gray-600">{item.type}</span>
              {item.file_path && (
                <p className="text-[10px] text-gray-600 truncate">{item.file_path}</p>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function NodeDetailPanel({
  repoId,
  nodeId,
  onClose,
  onSelectNode,
  onSelectFile,
}: NodeDetailPanelProps) {
  const [data, setData] = useState<NodeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [summarizing, setSummarizing] = useState(false);

  useEffect(() => {
    setLoading(true);
    getNode(repoId, nodeId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [repoId, nodeId]);

  const handleSummarize = async () => {
    if (!data) return;
    setSummarizing(true);
    try {
      const res = await summarizeNode(repoId, data.node.id);
      setData((prev) =>
        prev
          ? {
              ...prev,
              node: { ...prev.node, summary: res.summary, tags: res.tags },
            }
          : prev
      );
    } catch {
      // silent
    } finally {
      setSummarizing(false);
    }
  };

  return (
    <div
      className="fixed right-0 top-0 w-[480px] h-screen bg-[#0d0d0d] border-l border-gray-800 z-50 overflow-y-auto shadow-2xl transition-transform duration-300"
      style={{ transform: "translateX(0)" }}
    >
      {loading ? (
        <div className="p-6">
          <LoadingSpinner text="Loading node..." />
        </div>
      ) : !data ? (
        <div className="p-6 text-center text-gray-500">Node not found</div>
      ) : (
        <div className="p-6">
          {/* Header */}
          <div className="flex items-start justify-between gap-3 mb-5">
            <div>
              <h2 className="text-lg font-bold text-white break-all">{data.node.name}</h2>
              <div className="flex items-center gap-2 mt-1.5">
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded border ${
                    TYPE_COLORS[data.node.node_type] ?? "bg-gray-800 text-gray-400 border-gray-700"
                  }`}
                >
                  {data.node.node_type}
                </span>
                {data.node.is_async && (
                  <span className="px-2 py-0.5 text-xs bg-yellow-900/30 text-yellow-400 border border-yellow-700/30 rounded">
                    async
                  </span>
                )}
                {data.node.is_exported && (
                  <span className="px-2 py-0.5 text-xs bg-emerald-900/30 text-emerald-400 border border-emerald-700/30 rounded">
                    exported
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-gray-500 hover:text-gray-300 hover:bg-gray-800 rounded transition-colors shrink-0"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Summary */}
          <div className="mb-5">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Summary
            </p>
            {data.node.summary ? (
              <div>
                <p className="text-sm text-gray-300 leading-relaxed">{data.node.summary}</p>
                {data.node.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {data.node.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 text-[11px] bg-purple-900/20 text-purple-400 border border-purple-700/20 rounded-full"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={handleSummarize}
                disabled={summarizing}
                className="flex items-center gap-2 px-3 py-2 bg-purple-600/20 text-purple-400 border border-purple-700/30 rounded-lg hover:bg-purple-600/30 disabled:opacity-50 transition-colors text-sm"
              >
                {summarizing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                Summarize with AI
              </button>
            )}
          </div>

          {/* Location */}
          {data.file && (
            <div className="mb-5">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Location
              </p>
              <button
                onClick={() => data.file && onSelectFile?.(data.file.id)}
                className="text-sm text-blue-400 hover:text-blue-300 hover:underline font-mono break-all text-left"
              >
                {data.file.file_path}
              </button>
              {data.node.start_line != null && data.node.end_line != null && (
                <p className="text-xs text-gray-600 mt-0.5">
                  Lines {data.node.start_line} – {data.node.end_line}
                </p>
              )}
            </div>
          )}

          {/* Signature */}
          {data.node.signature && (
            <div className="mb-5">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Signature
              </p>
              <pre className="bg-[#0a0a0a] border border-gray-800 rounded-lg p-3 text-xs font-mono text-gray-300 overflow-x-auto">
                {data.node.signature}
              </pre>
            </div>
          )}

          {/* Raw code */}
          {data.node.raw_code && (
            <div className="mb-5">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Code
              </p>
              <pre className="bg-[#0a0a0a] border border-gray-800 rounded-lg p-3 text-xs font-mono text-gray-300 max-h-[300px] overflow-auto leading-relaxed">
                {highlightCode(data.node.raw_code)}
              </pre>
            </div>
          )}

          {/* Calls */}
          <RelationList
            label={`Calls ${data.calls.length} functions`}
            items={data.calls}
            onSelect={onSelectNode}
          />

          {/* Called by */}
          <RelationList
            label={`Called by ${data.called_by.length} functions`}
            items={data.called_by}
            onSelect={onSelectNode}
          />
        </div>
      )}
    </div>
  );
}
