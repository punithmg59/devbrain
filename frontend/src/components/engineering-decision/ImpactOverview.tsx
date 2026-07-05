import { useState } from 'react'
import { Globe, Building2, FileCode, Code2, Database, GitBranch, ChevronRight } from 'lucide-react'

interface ImpactCardProps {
  title: string
  icon: React.ReactNode
  count: number
  items: string[]
  color: string
  onExpand?: () => void
}

function ImpactCard({ title, icon, count, items, color, onExpand }: ImpactCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (count === 0) return null

  return (
    <button
      onClick={() => {
        setIsExpanded(!isExpanded)
        onExpand?.()
      }}
      className="w-full text-left rounded-xl border border-gray-800 bg-gray-900/40 p-6 hover:border-gray-700 hover:bg-gray-900/60 transition-all group"
    >
      <div className={`flex items-center gap-3 mb-4 ${color}`}>
        {icon}
        <span className="text-base font-semibold text-white">{title}</span>
        <span className="ml-auto text-sm text-gray-500 font-mono">{count}</span>
      </div>
      
      {!isExpanded ? (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>Click to view</span>
          <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </div>
      ) : (
        <div className="space-y-2 mt-4 pt-4 border-t border-gray-800">
          {items.slice(0, 8).map((item, i) => (
            <div key={i} className="flex items-start gap-2 text-sm text-gray-300">
              <ChevronRight className="w-4 h-4 mt-0.5 text-gray-600 shrink-0" />
              <span className="truncate">{item}</span>
            </div>
          ))}
          {items.length > 8 && (
            <div className="text-xs text-gray-500 mt-2">
              +{items.length - 8} more items
            </div>
          )}
        </div>
      )}
    </button>
  )
}

interface Props {
  affectedAPIs: string[]
  affectedServices: string[]
  affectedFiles: string[]
  affectedClasses: string[]
  affectedTables: string[]
  affectedWorkflows: string[]
}

export default function ImpactOverview({
  affectedAPIs,
  affectedServices,
  affectedFiles,
  affectedClasses,
  affectedTables,
  affectedWorkflows
}: Props) {
  const totalImpact = 
    affectedAPIs.length +
    affectedServices.length +
    affectedFiles.length +
    affectedClasses.length +
    affectedTables.length +
    affectedWorkflows.length

  if (totalImpact === 0) {
    return null
  }

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-white">Impact Overview</h2>
        <span className="text-sm text-gray-500">{totalImpact} total items affected</span>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <ImpactCard
          title="Affected APIs"
          icon={<Globe className="w-5 h-5 text-green-400" />}
          count={affectedAPIs.length}
          items={affectedAPIs}
          color="text-green-400"
        />
        <ImpactCard
          title="Affected Services"
          icon={<Building2 className="w-5 h-5 text-blue-400" />}
          count={affectedServices.length}
          items={affectedServices}
          color="text-blue-400"
        />
        <ImpactCard
          title="Affected Files"
          icon={<FileCode className="w-5 h-5 text-yellow-400" />}
          count={affectedFiles.length}
          items={affectedFiles}
          color="text-yellow-400"
        />
        <ImpactCard
          title="Affected Classes"
          icon={<Code2 className="w-5 h-5 text-purple-400" />}
          count={affectedClasses.length}
          items={affectedClasses}
          color="text-purple-400"
        />
        <ImpactCard
          title="Database Tables"
          icon={<Database className="w-5 h-5 text-red-400" />}
          count={affectedTables.length}
          items={affectedTables}
          color="text-red-400"
        />
        <ImpactCard
          title="Workflows"
          icon={<GitBranch className="w-5 h-5 text-cyan-400" />}
          count={affectedWorkflows.length}
          items={affectedWorkflows}
          color="text-cyan-400"
        />
      </div>
    </div>
  )
}
