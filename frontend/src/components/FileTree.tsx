import { useEffect, useState, useMemo } from "react";
import { Search, Folder, FolderOpen, File, ChevronRight, ChevronDown } from "lucide-react";
import { getFileTree } from "../services/repoDetailService";
import type { FileTreeNode } from "../types/repo";
import LoadingSpinner from "./ui/LoadingSpinner";
import ErrorState from "./ErrorState";

interface FileTreeProps {
  repoId: string;
  onSelectFile: (fileId: string) => void;
}

export default function FileTree({ repoId, onSelectFile }: FileTreeProps) {
  const [tree, setTree] = useState<FileTreeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    setLoading(true);
    setError(null);
    getFileTree(repoId)
      .then(setTree)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [repoId]);

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filteredTree = useMemo(() => {
    if (!filter) return tree;
    const lower = filter.toLowerCase();
    const filterNode = (node: FileTreeNode): FileTreeNode | null => {
      const match = node.name.toLowerCase().includes(lower);
      if (node.type === "folder") {
        const filteredChildren = node.children
          .map(filterNode)
          .filter((c): c is FileTreeNode => c !== null);
        if (match || filteredChildren.length) {
          return { ...node, children: filteredChildren };
        }
        return null;
      }
      return match ? node : null;
    };
    return tree
      .map(filterNode)
      .filter((n): n is FileTreeNode => n !== null);
  }, [tree, filter]);

  const renderNode = (node: FileTreeNode) => {
    const isFolder = node.type === "folder";
    const isOpen = expanded.has(node.id);
    return (
      <div key={node.id} className="ml-4">
        <div className="flex items-center py-1 cursor-pointer hover:bg-gray-800/30 rounded" onClick={() => (isFolder ? toggle(node.id) : onSelectFile(node.id))}>
          {isFolder ? (
            isOpen ? <FolderOpen className="w-4 h-4 mr-1" /> : <Folder className="w-4 h-4 mr-1" />
          ) : (
            <File className="w-4 h-4 mr-1" />
          )}
          <span className="text-sm text-gray-300 truncate flex-1">{node.name}</span>
          {isFolder && (
            <span className="text-xs text-gray-500 ml-2">{node.children.length}</span>
          )}
          {isFolder && (
            <button
              className="p-0.5 text-gray-400 hover:text-gray-200"
              onClick={(e) => {
                e.stopPropagation();
                toggle(node.id);
              }}
            >
              {isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>
          )}
        </div>
        {isFolder && isOpen && node.children.map(renderNode)}
      </div>
    );
  };

  if (loading) return <LoadingSpinner text="Loading file tree..." />;
  if (error) return <ErrorState message={error} retry={() => setLoading(true)} />;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 px-2 py-1 bg-gray-900/40 rounded">
        <Search className="w-4 h-4 text-gray-500" />
        <input
          type="text"
          placeholder="Search files..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="bg-transparent w-full focus:outline-none text-sm text-gray-200 placeholder-gray-500"
        />
      </div>
      <div className="max-h-[70vh] overflow-y-auto">
        {filteredTree.map(renderNode)}
      </div>
    </div>
  );
}
