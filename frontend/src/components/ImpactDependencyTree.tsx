import { useState, useMemo } from 'react'
import { ChevronRight, ChevronDown, FileCode, Server, Database, Key, Layers } from 'lucide-react'
import type { AffectedItemV2, ImpactReportV2 } from '../types/impact'

interface TreeNode {
  name: string
  nodeType: string
  filePath: string
  edgeType: string
  depth: number
  children: TreeNode[]
}

interface ImpactDependencyTreeProps {
  report: ImpactReportV2
  onSelectNode?: (name: string) => void
}

export default function ImpactDependencyTree({ report, onSelectNode }: ImpactDependencyTreeProps) {
  // Build tree from evidence chains
  const treeData = useMemo(() => {
    const rootName = report.resolved_node_name || report.query
    const rootType = report.resolved_node_type || 'function'
    const rootFile = report.resolved_file_path || ''

    const root: TreeNode = {
      name: rootName,
      nodeType: rootType,
      filePath: rootFile,
      edgeType: 'origin',
      depth: 0,
      children: [],
    }

    // Helper to find or create a child node in a subtree
    const getOrCreateChild = (parent: TreeNode, name: string, depth: number): TreeNode => {
      let child = parent.children.find((c) => c.name === name)
      if (!child) {
        child = {
          name,
          nodeType: 'function', // Default, will refine if matches affected item
          filePath: '',
          edgeType: 'calls',
          depth,
          children: [],
        }
        parent.children.push(child)
      }
      return child
    }

    // Combine all items with evidence
    const allItems: AffectedItemV2[] = [
      ...report.direct_callers,
      ...report.indirect_callers,
      ...report.affected_apis,
      ...report.affected_classes,
      ...report.affected_auth,
      ...report.affected_tables,
      ...report.affected_services,
    ]

    // Sort items by depth to ensure we build parents first
    const sortedItems = [...allItems].sort((a, b) => (a.evidence.depth || 0) - (b.evidence.depth || 0))

    sortedItems.forEach((item) => {
      const chain = item.evidence.chain
      if (!chain || chain.length <= 1) return

      // Traverse/build path down the tree
      let current = root
      for (let i = 1; i < chain.length; i++) {
        const stepName = chain[i]
        current = getOrCreateChild(current, stepName, i)

        // If this is the leaf node of this chain, update its metadata
        if (i === chain.length - 1) {
          current.nodeType = item.node_type || current.nodeType
          current.filePath = item.file_path || current.filePath
          current.edgeType = item.evidence.edge_type || current.edgeType
        }
      }
    })

    return root
  }, [report])

  return (
    <div className="bg-[#18181b]/40 backdrop-blur-xl border border-white/5 rounded-2xl p-5 shadow-2xl flex flex-col h-full">
      <div className="mb-4">
        <h3 className="font-semibold text-sm text-gray-200 flex items-center gap-2">
          <Layers className="w-4 h-4 text-purple-400" />
          Upstream Dependency Tree
        </h3>
        <p className="text-xs text-gray-500">Trace who calls/uses this component recursively</p>
      </div>

      <div className="flex-1 overflow-y-auto max-h-[500px] pr-2 scrollbar-thin">
        <TreeBranch node={treeData} isRoot={true} onSelect={onSelectNode} />
      </div>
    </div>
  )
}

function TreeBranch({
  node,
  isRoot = false,
  onSelect,
}: {
  node: TreeNode
  isRoot?: boolean
  onSelect?: (name: string) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = node.children.length > 0

  const getNodeIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'api_route':
        return <Server className="w-3.5 h-3.5 text-pink-400 shrink-0" />
      case 'table':
      case 'database':
        return <Database className="w-3.5 h-3.5 text-orange-400 shrink-0" />
      case 'auth_dependency':
      case 'verify_token':
      case 'get_current_user':
        return <Key className="w-3.5 h-3.5 text-yellow-400 shrink-0" />
      case 'class':
        return <Layers className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
      default:
        return <FileCode className="w-3.5 h-3.5 text-purple-400 shrink-0" />
    }
  }

  const getEdgeBadge = (edge: string) => {
    if (edge === 'origin') return null
    return (
      <span className="text-[9px] px-1 py-0.2 rounded bg-white/5 text-gray-400 border border-white/5">
        {edge}
      </span>
    )
  }

  return (
    <div className="pl-3 border-l border-white/5 select-none my-1">
      <div className="flex items-center gap-1.5 py-1 group rounded hover:bg-white/[0.02] pr-2">
        {hasChildren ? (
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-0.5 rounded hover:bg-white/10 text-gray-500"
          >
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          </button>
        ) : (
          <span className="w-4 h-4"></span>
        )}

        <span className="flex items-center gap-1.5 cursor-pointer" onClick={() => onSelect?.(node.name)}>
          {getNodeIcon(node.nodeType)}
          <span
            className={`text-xs truncate max-w-[160px] ${
              isRoot ? 'font-bold text-purple-300' : 'text-gray-300 group-hover:text-white'
            }`}
            title={node.name}
          >
            {node.name}
          </span>
        </span>

        {getEdgeBadge(node.edgeType)}

        {node.filePath && (
          <span className="text-[10px] text-gray-600 truncate max-w-[120px] ml-auto group-hover:text-gray-500">
            {node.filePath.split('/').pop()}
          </span>
        )}
      </div>

      {hasChildren && expanded && (
        <div className="ml-1.5 mt-0.5">
          {node.children.map((child, idx) => (
            <TreeBranch key={`${child.name}-${idx}`} node={child} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  )
}
