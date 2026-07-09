import { useState } from 'react'
import { User, Link, Workflow, Import, Globe, ChevronRight } from 'lucide-react'

interface Props {
  reasons: string[]
}

interface ReasonItemProps {
  icon: React.ReactNode
  text: string
  onClick?: () => void
}

function ReasonItem({ icon, text, onClick }: ReasonItemProps) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 text-gray-400 hover:text-white transition-colors w-full text-left group"
    >
      <div className="text-gray-500 group-hover:text-purple-400 transition-colors">
        {icon}
      </div>
      <span className="text-sm">{text}</span>
      <ChevronRight className="w-4 h-4 ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
    </button>
  )
}

export default function WhySection({ reasons }: Props) {
  const [expanded, setExpanded] = useState(false)
  const visibleReasons = expanded ? reasons : reasons.slice(0, 8)

  const getIconForReason = (reason: string) => {
    const lower = reason.toLowerCase()
    if (lower.includes('used by') || lower.includes('caller')) return <User className="w-4 h-4" />
    if (lower.includes('referenced') || lower.includes('reference')) return <Link className="w-4 h-4" />
    if (lower.includes('flow') || lower.includes('workflow')) return <Workflow className="w-4 h-4" />
    if (lower.includes('import') || lower.includes('imported')) return <Import className="w-4 h-4" />
    if (lower.includes('api') || lower.includes('external') || lower.includes('public')) return <Globe className="w-4 h-4" />
    return <User className="w-4 h-4" />
  }

  return (
    <div className="rounded-2xl border border-[#333] bg-[#1a1a1a] p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Why DevBrain Reached This Decision</h2>
      <div className="space-y-2">
        {visibleReasons.map((reason, index) => (
          <ReasonItem
            key={index}
            icon={getIconForReason(reason)}
            text={reason}
            onClick={() => console.log('Navigate to evidence:', reason)}
          />
        ))}
      </div>
      {reasons.length > 8 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-4 text-sm text-purple-400 hover:text-purple-300 transition-colors"
        >
          {expanded ? 'Show Less' : `View All Evidence (${reasons.length})`}
        </button>
      )}
    </div>
  )
}
