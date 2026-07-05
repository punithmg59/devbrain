import { useState } from 'react'
import { ChevronDown, ChevronUp, Search, ArrowRight, Layers, GitBranch, FileText } from 'lucide-react'

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
  centrality,
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
    <div className="rounded-2xl border border-gray-800 bg-gray-900/30 overflow-hidden mb-8">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-8 py-5 hover:bg-gray-800/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gray-800">
            <Search className="w-5 h-5 text-gray-400" />
          </div>
          <span className="font-semibold text-white text-lg">Supporting Evidence</span>
          <span className="text-sm text-gray-500">Advanced analysis details</span>
        </div>
        {isOpen ? <ChevronUp className="w-5 h-5 text-gray-500" /> : <ChevronDown className="w-5 h-5 text-gray-500" />}
      </button>

      {isOpen && (
        <div className="px-8 pb-8 space-y-6">
          {/* Centrality Score */}
          {centrality > 0 && (
            <div className="bg-gray-800/50 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-purple-400" />
                  <span className="font-semibold text-white">Dependency Centrality</span>
                </div>
                <span className="text-2xl font-bold text-purple-400">{centrality}</span>
              </div>
              <p className="text-sm text-gray-400">
                This component has {centrality > 0.7 ? 'high' : centrality > 0.4 ? 'moderate' : 'low'} influence in the dependency graph.
              </p>
            </div>
          )}

          {/* Risk Factors */}
          {riskFactors.length > 0 && (
            <div>
              <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-orange-400" />
                Risk Factors
              </h4>
              <div className="space-y-2">
                {riskFactors.map((factor, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-gray-800/50">
                    <ArrowRight className="w-4 h-4 text-orange-400 shrink-0" />
                    <span className="text-sm text-gray-300">{factor}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Callers */}
          {topCallers.length > 0 && (
            <div>
              <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                <ArrowRight className="w-4 h-4 text-blue-400 rotate-180" />
                Top Callers
              </h4>
              <div className="space-y-2">
                {topCallers.slice(0, 10).map((caller, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-gray-800/50">
                    <ArrowRight className="w-4 h-4 text-blue-400 rotate-180 shrink-0" />
                    <span className="text-sm text-gray-300 font-mono">{caller}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Critical Dependencies */}
          {criticalDependencies.length > 0 && (
            <div>
              <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                <Layers className="w-4 h-4 text-red-400" />
                Critical Dependencies
              </h4>
              <div className="space-y-2">
                {criticalDependencies.slice(0, 10).map((dep, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-gray-800/50">
                    <ArrowRight className="w-4 h-4 text-red-400 shrink-0" />
                    <span className="text-sm text-gray-300 font-mono">{dep}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Graph References */}
          {graphReferences.length > 0 && (
            <div>
              <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-green-400" />
                Graph References
              </h4>
              <div className="space-y-2">
                {graphReferences.slice(0, 10).map((ref, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-gray-800/50">
                    <ArrowRight className="w-4 h-4 text-green-400 shrink-0" />
                    <span className="text-sm text-gray-300 font-mono">{ref}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Repository Paths */}
          {repositoryPaths.length > 0 && (
            <div>
              <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4 text-yellow-400" />
                Repository Paths
              </h4>
              <div className="space-y-2">
                {repositoryPaths.slice(0, 10).map((path, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-gray-800/50">
                    <ArrowRight className="w-4 h-4 text-yellow-400 shrink-0" />
                    <span className="text-sm text-gray-300 font-mono">{path}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
