import { useState } from 'react'
import { ChevronDown, ChevronRight, Zap, Diamond, Hexagon, Braces } from 'lucide-react'
import { AffectedNode } from '../../types/impact'

interface Props {
  affectedApis: AffectedNode[]
  affectedServices: AffectedNode[]
  affectedTables: AffectedNode[]
  affectedNodes: AffectedNode[]
  onNodeClick: (node: AffectedNode) => void
}

export function AffectedNodesList({ 
  affectedApis, 
  affectedServices, 
  affectedTables, 
  affectedNodes,
  onNodeClick 
}: Props) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['apis', 'services'])
  )

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  const getRiskDotColor = (level: string | number) => {
    const levelStr = typeof level === 'number' 
      ? level >= 80 ? 'critical' : level >= 60 ? 'high' : level >= 40 ? 'medium' : 'low'
      : level
    switch (levelStr.toLowerCase()) {
      case 'critical': return 'bg-red-400'
      case 'high': return 'bg-amber-400'
      case 'medium': return 'bg-indigo-400'
      case 'low': return 'bg-green-400'
      default: return 'bg-gray-400'
    }
  }

  const Section = ({ 
    title, 
    icon, 
    items, 
    sectionKey 
  }: { 
    title: string
    icon: React.ReactNode
    items: AffectedNode[]
    sectionKey: string 
  }) => {
    if (items.length === 0) return null

    const isExpanded = expandedSections.has(sectionKey)

    return (
      <div className="border border-white/10 rounded-lg bg-[#161B22]">
        <button
          onClick={() => toggleSection(sectionKey)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
        >
          <div className="flex items-center gap-2">
            {icon}
            <span className="text-sm font-medium text-white">{title}</span>
            <span className="text-xs text-gray-500">({items.length})</span>
          </div>
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
        </button>

        {isExpanded && (
          <div className="border-t border-white/10">
            {items.map((node) => (
              <button
                key={node.id}
                onClick={() => onNodeClick(node)}
                className="w-full px-4 py-2.5 hover:bg-white/5 transition-colors flex items-center gap-3 border-b border-white/5 last:border-0"
              >
                <div className={`w-2 h-2 rounded-full ${getRiskDotColor(node.risk_score)}`} />
                <span className="flex-1 text-left text-sm text-white truncate">{node.name}</span>
                <span className="text-xs text-gray-500 truncate max-w-32">{node.file_path}</span>
                <span className="text-[10px] text-gray-600 font-mono">depth {node.depth}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  const totalAffected = affectedApis.length + affectedServices.length + affectedTables.length + affectedNodes.length

  if (totalAffected === 0) {
    return (
      <div className="p-6 rounded-lg bg-[#161B22] border border-white/10 text-center">
        <p className="text-sm text-gray-500">No components affected</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <Section
        title="APIs Affected"
        icon={<Zap className="w-4 h-4 text-purple-400" />}
        items={affectedApis}
        sectionKey="apis"
      />
      <Section
        title="Services Affected"
        icon={<Diamond className="w-4 h-4 text-blue-400" />}
        items={affectedServices}
        sectionKey="services"
      />
      <Section
        title="Database Tables"
        icon={<Hexagon className="w-4 h-4 text-amber-400" />}
        items={affectedTables}
        sectionKey="tables"
      />
      <Section
        title="Other Components"
        icon={<Braces className="w-4 h-4 text-gray-400" />}
        items={affectedNodes}
        sectionKey="other"
      />
    </div>
  )
}
