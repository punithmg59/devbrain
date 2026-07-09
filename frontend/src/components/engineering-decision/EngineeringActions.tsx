import { useState } from 'react'
import { Network, Layers, BarChart3, FileText, TestTube, Download, Share2, ChevronDown, ChevronUp, ArrowRight } from 'lucide-react'

interface PrimaryActionProps {
  icon: React.ReactNode
  iconBg: string
  title: string
  description: string
  onClick?: () => void
}

function PrimaryAction({ icon, iconBg, title, description, onClick }: PrimaryActionProps) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-between p-4 bg-[#2a2a2a] hover:bg-[#333] rounded-lg transition-colors group"
    >
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${iconBg}`}>
          {icon}
        </div>
        <div className="text-left">
          <div className="font-medium text-white">{title}</div>
          <div className="text-sm text-gray-500">{description}</div>
        </div>
      </div>
      <ArrowRight className="w-4 h-4 text-gray-500 group-hover:text-white rotate-180 transition-colors" />
    </button>
  )
}

interface SecondaryActionProps {
  icon: React.ReactNode
  title: string
  onClick?: () => void
}

function SecondaryAction({ icon, title, onClick }: SecondaryActionProps) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 p-3 text-sm text-gray-400 hover:text-white hover:bg-[#2a2a2a] rounded-lg transition-colors"
    >
      {icon}
      <span>{title}</span>
    </button>
  )
}

interface Props {
  onShowCallers?: () => void
  onShowSimulation?: () => void
  onOpenDependencyGraph?: () => void
  onGenerateMigrationPlan?: () => void
  onGenerateTestingChecklist?: () => void
  onExportReport?: () => void
  onShareWithTeam?: () => void
}

export default function EngineeringActions({
  onShowCallers,
  onShowSimulation,
  onOpenDependencyGraph,
  onGenerateMigrationPlan,
  onGenerateTestingChecklist,
  onExportReport,
  onShareWithTeam
}: Props) {
  const [showMoreActions, setShowMoreActions] = useState(false)

  return (
    <div className="rounded-2xl border border-[#333] bg-[#1a1a1a] p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Actions</h2>
      <div className="space-y-3">
        {/* Primary Action 1 */}
        <PrimaryAction
          icon={<Network className="w-5 h-5 text-purple-400" />}
          iconBg="bg-purple-500/10"
          title="Show All Callers"
          description="See complete dependency graph"
          onClick={onShowCallers}
        />

        {/* Primary Action 2 */}
        <PrimaryAction
          icon={<BarChart3 className="w-5 h-5 text-cyan-400" />}
          iconBg="bg-cyan-500/10"
          title="Simulate Change"
          description="Predict cascade effects"
          onClick={onShowSimulation}
        />

        {/* Primary Action 3 */}
        <PrimaryAction
          icon={<Layers className="w-5 h-5 text-blue-400" />}
          iconBg="bg-blue-500/10"
          title="Dependency Graph"
          description="Interactive visualization"
          onClick={onOpenDependencyGraph}
        />

        {/* More Actions Toggle */}
        <button
          onClick={() => setShowMoreActions(!showMoreActions)}
          className="w-full flex items-center justify-between p-3 text-sm text-gray-500 hover:text-white transition-colors"
        >
          <span>{showMoreActions ? 'Show Less' : 'More Actions'}</span>
          {showMoreActions ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {/* Secondary Actions */}
        {showMoreActions && (
          <div className="space-y-2 pt-2 border-t border-[#333]">
            <SecondaryAction
              icon={<FileText className="w-4 h-4" />}
              title="Migration Plan"
              onClick={onGenerateMigrationPlan}
            />
            <SecondaryAction
              icon={<TestTube className="w-4 h-4" />}
              title="Testing Checklist"
              onClick={onGenerateTestingChecklist}
            />
            <SecondaryAction
              icon={<Download className="w-4 h-4" />}
              title="Export Report"
              onClick={onExportReport}
            />
            <SecondaryAction
              icon={<Share2 className="w-4 h-4" />}
              title="Share with Team"
              onClick={onShareWithTeam}
            />
          </div>
        )}
      </div>
    </div>
  )
}
