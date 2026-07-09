import { useState } from 'react'
import { ChevronDown, ChevronUp, FileText } from 'lucide-react'

interface Props {
  topCallers: string[]
  criticalDependencies: string[]
  graphReferences: string[]
  repositoryPaths: string[]
  centrality: number
  riskFactors: string[]
}

export default function SupportingEvidence({
  topCallers,
  criticalDependencies,
  graphReferences,
  repositoryPaths,
  riskFactors
}: Props) {
  const [isOpen, setIsOpen] = useState(false)

  const hasContent = 
    topCallers.length > 0 ||
    criticalDependencies.length > 0 ||
    graphReferences.length > 0 ||
    repositoryPaths.length > 0 ||
    riskFactors.length > 0

  if (!hasContent) {
    return null
  }

  return (
    <button
      onClick={() => setIsOpen(!isOpen)}
      className="w-full flex items-center justify-between p-4 rounded-xl border border-[#333] bg-[#1a1a1a] hover:bg-[#2a2a2a] transition-colors"
    >
      <div className="flex items-center gap-3">
        <FileText className="w-4 h-4 text-gray-500" />
        <span className="text-sm text-gray-500">Supporting Evidence</span>
      </div>
      {isOpen ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
    </button>
  )
}
