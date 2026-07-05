import { Network, Layers, FileText, TestTube, Search, BarChart3, Download, ExternalLink, ArrowRight, GitCompare } from 'lucide-react'

interface ActionCardProps {
  icon: React.ReactNode
  title: string
  description: string
  shortcut?: string
  onClick?: () => void
}

function ActionCard({ icon, title, description, shortcut, onClick }: ActionCardProps) {
  return (
    <button
      onClick={onClick || (() => {})}
      className="w-full text-left p-6 rounded-xl border border-gray-800 bg-gray-900/40 hover:border-purple-500/50 hover:bg-purple-950/10 transition-all group relative overflow-hidden"
    >
      <div className="absolute top-0 right-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity">
        {shortcut && (
          <kbd className="px-2 py-1 text-xs text-gray-500 bg-gray-800 rounded border border-gray-700">
            {shortcut}
          </kbd>
        )}
      </div>

      <div className="flex items-start gap-4">
        <div className="p-3 rounded-xl bg-gray-800 group-hover:bg-purple-900/30 transition-colors shrink-0">
          {icon}
        </div>
        <div className="flex-1">
          <h4 className="font-semibold text-white mb-2 text-lg">{title}</h4>
          <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
        </div>
        <ArrowRight className="w-5 h-5 text-gray-600 group-hover:text-purple-400 transition-colors mt-1 shrink-0" />
      </div>
    </button>
  )
}

interface Props {
  onAction?: (action: string) => void
  onShowCallers?: () => void
  onShowSimulation?: () => void
}

export default function EngineeringActions({ onAction, onShowCallers, onShowSimulation }: Props) {
  const actions = [
    {
      id: 'show-callers',
      icon: <Network className="w-5 h-5 text-purple-400" />,
      title: 'Show All Callers',
      description: 'View complete dependency graph of all calling functions',
      shortcut: '⌘K',
      onClick: onShowCallers
    },
    {
      id: 'simulate-change',
      icon: <BarChart3 className="w-5 h-5 text-cyan-400" />,
      title: 'Simulate Change',
      description: 'Predict what happens after making this change',
      shortcut: '⌘S',
      onClick: onShowSimulation
    },
    {
      id: 'dependency-graph',
      icon: <Layers className="w-5 h-5 text-blue-400" />,
      title: 'Open Dependency Graph',
      description: 'Interactive visualization of the entire dependency tree',
      shortcut: '⌘G'
    },
    {
      id: 'migration-plan',
      icon: <FileText className="w-5 h-5 text-green-400" />,
      title: 'Generate Migration Plan',
      description: 'Step-by-step guide for safe refactoring',
      shortcut: '⌘M'
    },
    {
      id: 'test-checklist',
      icon: <TestTube className="w-5 h-5 text-yellow-400" />,
      title: 'Generate Testing Checklist',
      description: 'Comprehensive test coverage recommendations',
      shortcut: '⌘T'
    },
    {
      id: 'estimate-effort',
      icon: <BarChart3 className="w-5 h-5 text-cyan-400" />,
      title: 'Estimate Refactoring Effort',
      description: 'Time and complexity estimates for the change',
      shortcut: '⌘E'
    },
    {
      id: 'locate-critical',
      icon: <Search className="w-5 h-5 text-orange-400" />,
      title: 'Locate Critical Files',
      description: 'Find high-risk files requiring special attention',
      shortcut: '⌘F'
    },
    {
      id: 'export-report',
      icon: <Download className="w-5 h-5 text-gray-400" />,
      title: 'Export Report',
      description: 'Download this analysis as a PDF document',
      shortcut: '⌘S'
    },
    {
      id: 'open-github',
      icon: <ExternalLink className="w-5 h-5 text-purple-400" />,
      title: 'Open in GitHub',
      description: 'View affected files directly in your repository',
      shortcut: '⌘O'
    },
    {
      id: 'compare-branch',
      icon: <GitCompare className="w-5 h-5 text-green-400" />,
      title: 'Compare with Main Branch',
      description: 'See the diff between current and main branch',
      shortcut: '⌘D'
    }
  ]

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-white">Engineering Actions</h2>
        <span className="text-sm text-gray-500">Interactive tools</span>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {actions.map((action) => (
          <ActionCard
            key={action.id}
            icon={action.icon}
            title={action.title}
            description={action.description}
            shortcut={action.shortcut}
            onClick={action.onClick || (() => onAction?.(action.id))}
          />
        ))}
      </div>
    </div>
  )
}
