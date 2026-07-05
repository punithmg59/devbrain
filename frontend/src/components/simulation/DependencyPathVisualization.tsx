import { ChevronRight, Circle, Target } from 'lucide-react'
import type { CascadeChain } from '../../types/simulation'

interface Props {
  cascadeChains: CascadeChain[]
}

export default function DependencyPathVisualization({ cascadeChains }: Props) {
  if (!cascadeChains || cascadeChains.length === 0) {
    return null
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'border-red-500/30 bg-red-950/20'
      case 'high':
        return 'border-orange-500/30 bg-orange-950/20'
      case 'medium':
        return 'border-yellow-500/30 bg-yellow-950/20'
      case 'low':
        return 'border-green-500/30 bg-green-950/20'
      default:
        return 'border-gray-500/30 bg-gray-950/20'
    }
  }

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/20 text-red-400'
      case 'high':
        return 'bg-orange-500/20 text-orange-400'
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400'
      case 'low':
        return 'bg-green-500/20 text-green-400'
      default:
        return 'bg-gray-500/20 text-gray-400'
    }
  }

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900/30 p-8">
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2 rounded-lg bg-purple-500/10">
          <Target className="w-5 h-5 text-purple-400" />
        </div>
        <h2 className="text-xl font-semibold text-white">Critical Dependency Paths</h2>
        <span className="text-sm text-gray-500">{cascadeChains.length} chains detected</span>
      </div>

      <div className="space-y-6">
        {cascadeChains.map((chain) => (
          <div key={chain.id} className={`rounded-xl border p-6 ${getSeverityColor(chain.severity)}`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="font-semibold text-white">{chain.startComponent}</span>
                <ChevronRight className="w-4 h-4 text-gray-500" />
                <span className="font-semibold text-white">{chain.endComponent}</span>
              </div>
              <span className={`px-3 py-1 text-xs font-medium rounded-full capitalize ${getSeverityBadge(chain.severity)}`}>
                {chain.severity}
              </span>
            </div>

            <div className="space-y-3">
              {chain.steps.map((step, index) => (
                <div key={step.id} className="relative flex items-start gap-4">
                  {/* Vertical line */}
                  {index < chain.steps.length - 1 && (
                    <div className="absolute left-[19px] top-8 w-0.5 h-full bg-gray-700" />
                  )}

                  {/* Step indicator */}
                  <div className="relative z-10">
                    <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center ${
                      step.impact === 'critical'
                        ? 'border-red-500 bg-red-500/10'
                        : step.impact === 'error'
                        ? 'border-orange-500 bg-orange-500/10'
                        : 'border-gray-500 bg-gray-500/10'
                    }`}>
                      <Circle className="w-4 h-4 text-gray-400 fill-gray-400" />
                    </div>
                  </div>

                  {/* Step content */}
                  <div className="flex-1 pt-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-white">{step.component}</span>
                      <span className="px-2 py-0.5 text-xs font-medium bg-gray-800 text-gray-400 rounded-full capitalize">
                        {step.componentType}
                      </span>
                    </div>
                    <p className="text-sm text-gray-400">{step.description}</p>
                  </div>

                  {/* Depth indicator */}
                  <div className="text-sm text-gray-500">
                    Depth {step.depth}
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
