import { Clock, CheckCircle } from 'lucide-react'

interface TimelineStep {
  title: string
  description: string
  timeEstimate: string
  status: 'current' | 'pending' | 'completed'
}

interface Props {
  steps: TimelineStep[]
  onGenerateChecklist?: () => void
  onExportPlan?: () => void
}

export default function RecommendedApproach({ steps, onGenerateChecklist, onExportPlan }: Props) {
  return (
    <div className="rounded-2xl border border-[#333] bg-[#1a1a1a] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Recommended Engineering Approach</h2>
        <div className="flex gap-2">
          {onGenerateChecklist && (
            <button
              onClick={onGenerateChecklist}
              className="px-3 py-1.5 text-sm bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
            >
              Generate Checklist
            </button>
          )}
          {onExportPlan && (
            <button
              onClick={onExportPlan}
              className="px-3 py-1.5 text-sm bg-[#2a2a2a] hover:bg-[#333] text-white rounded-lg transition-colors"
            >
              Export Plan
            </button>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {steps.map((step, index) => (
          <div key={index} className="relative">
            {/* Vertical line */}
            {index < steps.length - 1 && (
              <div className="absolute left-[11px] top-8 w-0.5 h-full border-l-2 border-dashed border-gray-700" />
            )}

            <div className="flex items-start gap-4">
              {/* Step indicator */}
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium shrink-0 ${
                step.status === 'current' 
                  ? 'bg-purple-600 text-white' 
                  : step.status === 'completed'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-700 text-gray-400'
              }`}>
                {step.status === 'completed' ? <CheckCircle className="w-3 h-3" /> : index + 1}
              </div>

              {/* Step content */}
              <div className="flex-1 pb-4">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-medium text-white">{step.title}</h3>
                  <div className="flex items-center gap-1 text-xs text-gray-500">
                    <Clock className="w-3 h-3" />
                    <span>{step.timeEstimate}</span>
                  </div>
                </div>
                <p className="text-sm text-gray-400">{step.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
