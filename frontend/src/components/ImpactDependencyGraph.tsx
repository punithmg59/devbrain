import { useEffect, useMemo, useRef, useState } from 'react'
import type { ImpactGraph } from '../types/impact'

const TIER_COLOR: Record<string, string> = {
  safe: '#22c55e',
  low: '#4ade80',
  medium: '#eab308',
  high: '#f97316',
  critical: '#ef4444',
}

interface SimNode {
  id: string
  name: string
  risk_tier: string
  is_source: boolean
  x: number
  y: number
  vx: number
  vy: number
}

interface Props {
  graph: ImpactGraph | null
  className?: string
}

export default function ImpactDependencyGraph({ graph, className = '' }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 800, h: 420 })
  const [expanded, setExpanded] = useState(true)
  const [positions, setPositions] = useState<SimNode[]>([])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect
      setSize({ w: Math.max(320, width), h: 420 })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const initialNodes = useMemo(() => {
    if (!graph?.nodes.length) return []
    const cx = size.w / 2
    const cy = size.h / 2
    return graph.nodes.map((n, i) => {
      const angle = (i / graph.nodes.length) * Math.PI * 2
      const r = n.is_source ? 0 : 80 + n.depth * 45
      return {
        id: n.id,
        name: n.name,
        risk_tier: n.risk_tier,
        is_source: n.is_source,
        x: cx + Math.cos(angle) * r,
        y: cy + Math.sin(angle) * r,
        vx: 0,
        vy: 0,
      }
    })
  }, [graph, size.w, size.h])

  useEffect(() => {
    if (!graph?.nodes.length) {
      setPositions([])
      return
    }

    const nodes: SimNode[] = initialNodes.map((n) => ({ ...n }))
    const edges = graph.edges
    const idSet = new Set(nodes.map((n) => n.id))

    let frame = 0
    const maxFrames = 120

    const tick = () => {
      const cx = size.w / 2
      const cy = size.h / 2

      for (const n of nodes) {
        if (n.is_source) {
          n.x = cx
          n.y = cy
          n.vx = 0
          n.vy = 0
          continue
        }
        n.vx += (cx - n.x) * 0.002
        n.vy += (cy - n.y) * 0.002
      }

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i]
          const b = nodes[j]
          const dx = b.x - a.x
          const dy = b.y - a.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          const force = 1200 / (dist * dist)
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force
          if (!a.is_source) {
            a.vx -= fx
            a.vy -= fy
          }
          if (!b.is_source) {
            b.vx += fx
            b.vy += fy
          }
        }
      }

      for (const e of edges) {
        if (!idSet.has(e.from_id) || !idSet.has(e.to_id)) continue
        const a = nodes.find((n) => n.id === e.from_id)
        const b = nodes.find((n) => n.id === e.to_id)
        if (!a || !b) continue
        const dx = b.x - a.x
        const dy = b.y - a.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = (dist - 90) * 0.05
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        if (!a.is_source) {
          a.vx += fx
          a.vy += fy
        }
        if (!b.is_source) {
          b.vx -= fx
          b.vy -= fy
        }
      }

      for (const n of nodes) {
        if (n.is_source) continue
        n.vx *= 0.85
        n.vy *= 0.85
        n.x += n.vx
        n.y += n.vy
        n.x = Math.max(40, Math.min(size.w - 40, n.x))
        n.y = Math.max(40, Math.min(size.h - 40, n.y))
      }

      frame++
      if (frame < maxFrames) {
        requestAnimationFrame(tick)
      }
      setPositions(nodes.map((n) => ({ ...n })))
    }

    requestAnimationFrame(tick)
  }, [graph, initialNodes, size.w, size.h])

  if (!graph?.nodes.length) {
    return (
      <div className={`rounded-xl border border-gray-800 bg-gray-900/50 p-8 text-center text-gray-500 text-sm ${className}`}>
        No graph data to visualize
      </div>
    )
  }

  const posMap = new Map(positions.map((p) => [p.id, p]))

  return (
    <div className={`rounded-xl border border-gray-800 bg-[#0a0a0c] overflow-hidden ${className}`}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <div>
          <h3 className="text-sm font-semibold text-white">Blast radius graph</h3>
          <p className="text-xs text-gray-500">
            {graph.nodes.length} nodes · {graph.edges.length} verified edges
          </p>
        </div>
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="text-xs px-2 py-1 rounded border border-gray-700 text-gray-400 hover:text-white"
        >
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>
      {expanded && (
        <div ref={containerRef} className="w-full">
          <svg width={size.w} height={size.h} className="block">
            <defs>
              <marker
                id="arrow"
                markerWidth="8"
                markerHeight="8"
                refX="6"
                refY="3"
                orient="auto"
              >
                <path d="M0,0 L6,3 L0,6 Z" fill="#4b5563" />
              </marker>
            </defs>
            {graph.edges.map((e) => {
              const from = posMap.get(e.from_id)
              const to = posMap.get(e.to_id)
              if (!from || !to) return null
              return (
                <line
                  key={`${e.from_id}-${e.to_id}`}
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke="#374151"
                  strokeWidth={1}
                  markerEnd="url(#arrow)"
                />
              )
            })}
            {graph.nodes.map((n) => {
              const p = posMap.get(n.id)
              if (!p) return null
              const color = TIER_COLOR[n.risk_tier] ?? TIER_COLOR.low
              const w = n.is_source ? 100 : 72
              const h = 28
              return (
                <g key={n.id}>
                  <rect
                    x={p.x - w / 2}
                    y={p.y - h / 2}
                    width={w}
                    height={h}
                    rx={6}
                    fill="#111827"
                    stroke={color}
                    strokeWidth={n.is_source ? 2.5 : 1.5}
                  />
                  <text
                    x={p.x}
                    y={p.y + 4}
                    textAnchor="middle"
                    fill="#e5e7eb"
                    fontSize={10}
                    fontFamily="system-ui"
                  >
                    {n.name.length > 12 ? `${n.name.slice(0, 11)}…` : n.name}
                  </text>
                </g>
              )
            })}
          </svg>
          <div className="flex flex-wrap gap-3 px-4 pb-3 text-[10px] text-gray-500">
            {Object.entries(TIER_COLOR).map(([tier, color]) => (
              <span key={tier} className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full" style={{ background: color }} />
                {tier}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
