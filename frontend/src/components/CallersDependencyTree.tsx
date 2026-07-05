import { ChevronRight, Circle } from 'lucide-react'
import type { CallerNode } from '../types/callers'

interface Props {
  target: { name: string; type: string }
  callers: CallerNode[]
  maxDepth?: number
}

export default function CallersDependencyTree({ target, callers, maxDepth = 3 }: Props) {
  // Group callers by depth
  const byDepth: Record<number, CallerNode[]> = {}
  callers.forEach(caller => {
    const depth = caller.depth || 0
    if (depth <= maxDepth) {
      if (!byDepth[depth]) byDepth[depth] = []
      byDepth[depth].push(caller)
    }
  })

  // Sort each depth level by criticality then name
  Object.keys(byDepth).forEach(depth => {
    byDepth[Number(depth)].sort((a, b) => {
      if (a.critical && !b.critical) return -1
      if (!a.critical && b.critical) return 1
      return a.name.localeCompare(b.name)
    })
  })

  const depths = Object.keys(byDepth).map(Number).sort((a, b) => a - b)

  if (depths.length === 0) {
    return null
  }

  return (
    <div className="bg-gray-900/50 rounded-xl p-6 border border-gray-800">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-6">
        Dependency Tree (Depth {maxDepth})
      </h3>

      <div className="space-y-4">
        {/* Target Node */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-purple-500/20 border-2 border-purple-500 flex items-center justify-center">
            <Circle className="w-4 h-4 text-purple-400 fill-purple-400" />
          </div>
          <div>
            <div className="font-semibold text-white">{target.name}</div>
            <div className="text-xs text-gray-500 capitalize">{target.type}</div>
          </div>
        </div>

        {/* Dependency Levels */}
        {depths.map(depth => (
          <div key={depth} className="relative pl-8">
            {/* Vertical line */}
            {depth < maxDepth && (
              <div className="absolute left-3 top-8 w-0.5 h-full bg-gray-700" />
            )}

            {/* Level label */}
            <div className="text-xs text-gray-500 mb-3">
              Depth {depth} {depth === 1 ? '(Direct Callers)' : '(Indirect)'}
            </div>

            {/* Nodes at this depth */}
            <div className="space-y-2">
              {byDepth[depth].map((caller) => (
                <div key={caller.id} className="relative">
                  {/* Horizontal line */}
                  <div className="absolute left-[-20px] top-1/2 w-4 h-0.5 bg-gray-700" />

                  <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-800/50 border border-gray-700/50 hover:border-gray-600 transition-colors">
                    <ChevronRight className="w-4 h-4 text-gray-600 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-white truncate">{caller.name}</span>
                        {caller.critical && (
                          <span className="px-2 py-0.5 text-xs font-medium bg-orange-500/20 text-orange-400 rounded-full shrink-0">
                            Critical
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 truncate">{caller.file}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
