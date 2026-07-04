import { useEffect, useCallback, useMemo, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
} from '@xyflow/react'
import type { Node, Edge } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Search } from 'lucide-react'
import { ImpactResultV3, AffectedNode } from '../../types/impact'

interface Props {
  result: ImpactResultV3 | null
  onNodeClick: (node: AffectedNode) => void
}

// Custom node types
const TargetNode = ({ data }: { data: any }) => {
  return (
    <div className="px-4 py-3 rounded-lg border-2 border-red-500 bg-red-950 shadow-lg shadow-red-500/20 animate-pulse">
      <div className="text-[10px] text-red-400 font-bold mb-1">SELECTED</div>
      <div className="text-sm font-medium text-white">{data.label}</div>
    </div>
  )
}

const AffectedNodeComponent = ({ data }: { data: any }) => {
  const getRiskStyles = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical':
        return 'border-red-500 bg-red-950/60'
      case 'high':
        return 'border-amber-500 bg-amber-950/60'
      case 'medium':
        return 'border-indigo-500 bg-indigo-950/60'
      case 'low':
        return 'border-green-500/50 bg-green-950/30'
      default:
        return 'border-gray-500 bg-gray-950/30'
    }
  }

  const getNodeTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'function':
      case 'method':
        return 'ƒ'
      case 'class':
        return 'C'
      case 'api_route':
        return '⚡'
      case 'database_table':
        return '⬡'
      case 'service':
        return '◈'
      default:
        return '◆'
    }
  }

  return (
    <div 
      className={`px-3 py-2 rounded-lg border ${getRiskStyles(data.risk_level)} cursor-pointer hover:opacity-80 transition-opacity`}
      onClick={() => data.onNodeClick?.(data.originalNode)}
    >
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400">{getNodeTypeIcon(data.node_type)}</span>
        <span className="text-sm font-medium text-white truncate">{data.label}</span>
      </div>
    </div>
  )
}

const nodeTypes = {
  targetNode: TargetNode,
  affectedNode: AffectedNodeComponent,
}

export function BlastRadiusGraphV3({ result, onNodeClick }: Props) {
  const [nodes, setNodes] = useState<Node[]>([])
  const [edges, setEdges] = useState<Edge[]>([])

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds))
  }, [])

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes, eds))
  }, [])

  const buildGraphData = useCallback((res: ImpactResultV3) => {
    const newNodes: Node[] = []
    const newEdges: Edge[] = []

    // Add target node at center
    newNodes.push({
      id: res.node_id || res.resolved_node?.id || 'unknown',
      type: 'targetNode',
      position: { x: 0, y: 0 },
      data: {
        label: res.node_name || res.resolved_node?.name || 'Unknown',
        node_type: res.node_type || res.resolved_node?.node_type || 'unknown',
        isTarget: true,
      },
    })

    // Group affected nodes by depth
    const byDepth = new Map<number, AffectedNode[]>()
    res.affected_nodes.forEach(node => {
      const depth = node.depth || 1
      if (!byDepth.has(depth)) byDepth.set(depth, [])
      byDepth.get(depth)!.push(node)
    })

    // Position each depth ring
    const radii = [0, 220, 420, 620, 820]
    byDepth.forEach((nodesAtDepth, depth) => {
      const radius = radii[Math.min(depth, 4)]
      nodesAtDepth.forEach((node, i) => {
        const angle = (i / nodesAtDepth.length) * 2 * Math.PI - Math.PI / 2
        newNodes.push({
          id: node.id,
          type: 'affectedNode',
          position: {
            x: Math.cos(angle) * radius,
            y: Math.sin(angle) * radius,
          },
          data: {
            label: node.name,
            node_type: node.node_type,
            risk_level: node.risk_level,
            depth: node.depth,
            originalNode: node,
            onNodeClick,
          },
        })
      })
    })

    // Add edges from graph_edges
    if (res.graph_edges && res.graph_edges.length > 0) {
      res.graph_edges.forEach((edge: any, i: number) => {
        newEdges.push({
          id: `e${i}`,
          source: edge.source,
          target: edge.target,
          type: 'smoothstep',
          animated: edge.is_critical,
          style: {
            stroke: edge.is_critical ? '#EF4444' : '#6366F1',
            strokeWidth: edge.is_critical ? 2 : 1,
            opacity: 0.6,
          },
          markerEnd: {
            type: 'arrowclosed',
            color: edge.is_critical ? '#EF4444' : '#6366F1',
          },
        })
      })
    } else {
      // Fallback: draw edges from target to depth-1 nodes
      const depth1Nodes = byDepth.get(1) || []
      depth1Nodes.forEach((node, i) => {
        newEdges.push({
          id: `fallback-${i}`,
          source: res.node_id || res.resolved_node?.id || 'unknown',
          target: node.id,
          type: 'smoothstep',
          animated: false,
          style: {
            stroke: '#6366F1',
            strokeWidth: 1,
            opacity: 0.6,
          },
          markerEnd: {
            type: 'arrowclosed',
            color: '#6366F1',
          },
        })
      })
    }

    return { nodes: newNodes, edges: newEdges }
  }, [onNodeClick])

  useEffect(() => {
    if (result) {
      const { nodes: newNodes, edges: newEdges } = buildGraphData(result)
      setNodes(newNodes)
      setEdges(newEdges)
    } else {
      setNodes([])
      setEdges([])
    }
  }, [result, buildGraphData, setNodes, setEdges])

  const showMiniMap = useMemo(() => nodes.length > 10, [nodes.length])

  if (!result) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-[#0A0A0F]">
        <div className="text-center">
          <div className="p-4 rounded-full bg-white/5 mb-4 border border-white/10 inline-block">
            <Search className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">Select a component to analyze</h3>
          <p className="text-sm text-gray-500">
            Search above to find functions, classes, APIs, or tables
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full h-full bg-[#0A0A0F]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.1}
        maxZoom={2.5}
        nodesDraggable={true}
        defaultEdgeOptions={{
          type: 'smoothstep',
        }}
      >
        <Background color="#ffffff15" gap={20} />
        <Controls />
        {showMiniMap && <MiniMap />}
      </ReactFlow>
    </div>
  )
}
