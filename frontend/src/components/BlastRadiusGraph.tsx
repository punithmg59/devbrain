import { useMemo } from 'react'
import type { BlastRadiusV2, AffectedItemV2 } from '../types/impact'

interface BlastRadiusGraphProps {
  blastRadius: BlastRadiusV2
  resolvedNodeName: string | null
  resolvedNodeType: string | null
  directCallers: AffectedItemV2[]
  indirectCallers: AffectedItemV2[]
  affectedApis: AffectedItemV2[]
  affectedTables: AffectedItemV2[]
  affectedServices: AffectedItemV2[]
  onSelectNode?: (name: string) => void
}

interface GraphItem {
  id: string
  name: string
  type: string
  tier: 'direct' | 'indirect' | 'boundary'
  angle: number
  color: string
}

export default function BlastRadiusGraph({
  blastRadius,
  resolvedNodeName,
  resolvedNodeType,
  directCallers,
  indirectCallers,
  affectedApis,
  affectedTables,
  affectedServices,
  onSelectNode,
}: BlastRadiusGraphProps) {
  const centerName = resolvedNodeName || 'Target'
  const centerType = resolvedNodeType || 'function'

  // Map elements into coordinates
  const graphItems = useMemo(() => {
    const items: GraphItem[] = []

    // 1. Direct callers (Inner circle)
    directCallers.slice(0, 12).forEach((item, index, arr) => {
      const angle = (index / arr.length) * 2 * Math.PI
      items.push({
        id: `direct-${index}`,
        name: item.name,
        type: item.node_type,
        tier: 'direct',
        angle,
        color: '#a855f7', // Purple
      })
    })

    // 2. Indirect callers (Middle circle)
    indirectCallers.slice(0, 16).forEach((item, index, arr) => {
      const angle = ((index + 0.5) / arr.length) * 2 * Math.PI
      items.push({
        id: `indirect-${index}`,
        name: item.name,
        type: item.node_type,
        tier: 'indirect',
        angle,
        color: '#6366f1', // Indigo
      })
    })

    // 3. Boundaries: APIs, Tables, Services (Outer circle)
    const boundaries: { name: string; type: string; color: string }[] = []
    affectedApis.slice(0, 6).forEach((a) => boundaries.push({ name: a.name, type: 'api_route', color: '#ec4899' })) // Pink
    affectedTables.slice(0, 6).forEach((t) => boundaries.push({ name: t.name, type: 'table', color: '#f97316' })) // Orange
    affectedServices.slice(0, 6).forEach((s) => boundaries.push({ name: s.name, type: 'service', color: '#eab308' })) // Yellow

    boundaries.forEach((b, index, arr) => {
      const angle = (index / arr.length) * 2 * Math.PI
      items.push({
        id: `boundary-${index}`,
        name: b.name,
        type: b.type,
        tier: 'boundary',
        angle,
        color: b.color,
      })
    })

    return items
  }, [directCallers, indirectCallers, affectedApis, affectedTables, affectedServices])

  // Radial positions
  const r1 = 60  // Direct
  const r2 = 120 // Indirect
  const r3 = 180 // Boundaries

  const width = 440
  const height = 400
  const cx = width / 2
  const cy = height / 2

  return (
    <div className="relative flex flex-col items-center bg-[#18181b]/40 backdrop-blur-xl border border-white/5 rounded-2xl p-6 shadow-2xl">
      <div className="w-full flex justify-between items-center mb-4">
        <div>
          <h3 className="font-semibold text-sm text-gray-200">Blast Radius Visualizer</h3>
          <p className="text-xs text-gray-500">Interactive blast circles by proximity</p>
        </div>
        <div className="flex gap-4 text-[10px] text-gray-400">
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500 block"></span>
            <span>Direct ({blastRadius.direct_dependents})</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 block"></span>
            <span>Indirect ({blastRadius.indirect_dependents})</span>
          </div>
        </div>
      </div>

      <div className="relative w-full overflow-hidden flex justify-center items-center">
        <svg width={width} height={height} className="select-none">
          <defs>
            {/* Pulsing center glow */}
            <radialGradient id="centerGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#c084fc" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#a855f7" stopOpacity="0" />
            </radialGradient>
            
            {/* Subdued connector lines */}
            <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3f3f46" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#71717a" stopOpacity="0.05" />
            </linearGradient>
          </defs>

          {/* Orbits / Rings */}
          <circle cx={cx} cy={cy} r={r1} fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1" strokeDasharray="4 4" />
          <circle cx={cx} cy={cy} r={r2} fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1" strokeDasharray="6 4" />
          <circle cx={cx} cy={cy} r={r3} fill="none" stroke="rgba(255,255,255,0.02)" strokeWidth="1" />

          {/* Center Glow */}
          <circle cx={cx} cy={cy} r="45" fill="url(#centerGlow)" className="animate-pulse" />

          {/* Connector lines to direct nodes */}
          {graphItems.map((item) => {
            const r = item.tier === 'direct' ? r1 : item.tier === 'indirect' ? r2 : r3
            const tx = cx + r * Math.cos(item.angle)
            const ty = cy + r * Math.sin(item.angle)
            return (
              <line
                key={`line-${item.id}`}
                x1={cx}
                y1={cy}
                x2={tx}
                y2={ty}
                stroke="rgba(255,255,255,0.05)"
                strokeWidth={item.tier === 'direct' ? 1.5 : 1}
              />
            )
          })}

          {/* Render Nodes */}
          {graphItems.map((item) => {
            const r = item.tier === 'direct' ? r1 : item.tier === 'indirect' ? r2 : r3
            const tx = cx + r * Math.cos(item.angle)
            const ty = cy + r * Math.sin(item.angle)

            return (
              <g
                key={`node-${item.id}`}
                className="cursor-pointer group"
                onClick={() => onSelectNode?.(item.name)}
              >
                {/* Glow on hover */}
                <circle
                  cx={tx}
                  cy={ty}
                  r="9"
                  fill={item.color}
                  opacity="0"
                  className="transition-all duration-300 group-hover:opacity-20"
                />
                {/* Real Dot */}
                <circle
                  cx={tx}
                  cy={ty}
                  r={item.tier === 'direct' ? 5.5 : 4.5}
                  fill={item.color}
                  className="transition-all duration-300 group-hover:scale-125"
                />
                {/* Simple Tooltip on Node */}
                <title>{`${item.name} (${item.type})`}</title>
              </g>
            )
          })}

          {/* Center target Node */}
          <g className="cursor-default">
            <circle cx={cx} cy={cy} r="16" fill="#09090b" stroke="#a855f7" strokeWidth="2.5" />
            <circle cx={cx} cy={cy} r="6" fill="#a855f7" />
          </g>
        </svg>

        {/* Center overlay labels */}
        <div className="absolute flex flex-col items-center pointer-events-none text-center">
          <span className="text-[10px] uppercase tracking-wider text-purple-400 font-bold px-1.5 py-0.5 rounded bg-purple-500/10 border border-purple-500/20">
            {centerType}
          </span>
          <span className="text-xs font-semibold text-white mt-1 max-w-[120px] truncate">
            {centerName}
          </span>
        </div>
      </div>

      {/* Legend & Details */}
      <div className="w-full grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-white/5 text-[10px]">
        <div className="flex flex-col items-center p-2 rounded bg-white/[0.02]">
          <span className="text-pink-400 font-medium text-xs">{blastRadius.api_impact}</span>
          <span className="text-gray-500">APIs Impacted</span>
        </div>
        <div className="flex flex-col items-center p-2 rounded bg-white/[0.02]">
          <span className="text-orange-400 font-medium text-xs">{blastRadius.database_impact}</span>
          <span className="text-gray-500">Tables Used</span>
        </div>
        <div className="flex flex-col items-center p-2 rounded bg-white/[0.02]">
          <span className="text-yellow-400 font-medium text-xs">{blastRadius.service_impact}</span>
          <span className="text-gray-500">Services</span>
        </div>
      </div>
    </div>
  )
}
