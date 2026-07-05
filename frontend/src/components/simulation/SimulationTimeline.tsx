import { ArrowDown, AlertTriangle, XCircle, Info, CheckCircle } from 'lucide-react'
import type { SimulationStep } from '../../types/simulation'

interface Props {
  steps: SimulationStep[]
  changeType: string
}

export default function SimulationTimeline({ steps, changeType }: Props) {
  if (!steps || steps.length === 0) {
    return null
  }

  const getImpactIcon = (impact: string) => {
    switch (impact) {
      case 'critical':
        return <XCircle className="w-5 h-5 text-red-400" />
      case 'error':
        return <AlertTriangle className="w-5 h-5 text-orange-400" />
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-400" />
      case 'info':
        return <Info className="w-5 h-5 text-blue-400" />
      default:
        return <CheckCircle className="w-5 h-5 text-green-400" />
    }
  }

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'critical':
        return 'border-red-500/30 bg-red-950/20'
      case 'error':
        return 'border-orange-500/30 bg-orange-950/20'
      case 'warning':
        return 'border-yellow-500/30 bg-yellow-950/20'
      case 'info':
        return 'border-blue-500/30 bg-blue-950/20'
      default:
        return 'border-green-500/30 bg-green-950/20'
    }
  }

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900/30 p-8">
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2 rounded-lg bg-purple-500/10">
          <ArrowDown className="w-5 h-5 text-purple-400" />
        </div>
        <h2 className="text-xl font-semibold text-white">Change Simulation Timeline</h2>
        <span className="text-sm text-gray-500 capitalize">{changeType}</span>
      </div>

      <div className="space-y-0">
        {steps.map((step, index) => (
          <div key={step.id} className="relative">
            {/* Vertical line */}
            {index < steps.length - 1 && (
              <div className="absolute left[19px] top-8 w-0.5 h-full bg-gray-700" />
            )}

            <div className="flex gap-6 pb-8 last:pb-0">
              {/* Status icon */}
              <div className="relative z-10">
                <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center ${getImpactColor(step.impact)}`}>
                  {getImpactIcon(step.impact)}
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 pt-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold text-white">{step.description}</h3>
                  <span className="px-2 py-0.5 text-xs font-medium bg-gray-800 text-gray-400 rounded-full capitalize">
                    {step.componentType}
                  </span>
                </div>
                <p className="text-sm text-gray-400">
                  Component: <span className="text-gray-300">{step.component}</span>
                  {step.depth > 0 && (
                    <span className="ml-3">Depth: <span className="text-gray-300">{step.depth}</span></span>
                  )}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
