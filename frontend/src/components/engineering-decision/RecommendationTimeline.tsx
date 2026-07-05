import { ArrowDown, CheckCircle, Circle } from 'lucide-react'

interface TimelineStep {
  title: string
  description: string
  status: 'completed' | 'current' | 'pending'
}

interface Props {
  steps: TimelineStep[]
}

export default function RecommendationTimeline({ steps }: Props) {
  if (!steps || steps.length === 0) {
    return null
  }

  return (
    <div className="rounded-2xl border border-purple-500/20 bg-purple-950/10 p-8 mb-8">
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2 rounded-lg bg-purple-500/10">
          <CheckCircle className="w-5 h-5 text-purple-400" />
        </div>
        <h2 className="text-xl font-semibold text-white">Recommended Engineering Approach</h2>
      </div>
      
      <div className="space-y-0">
        {steps.map((step, index) => (
          <div key={index} className="relative">
            {/* Vertical line */}
            {index < steps.length - 1 && (
              <div className="absolute left-4 top-8 w-0.5 h-full bg-gray-700" />
            )}
            
            <div className="flex gap-6 pb-8 last:pb-0">
              {/* Status icon */}
              <div className="relative z-10">
                {step.status === 'completed' ? (
                  <div className="w-8 h-8 rounded-full bg-green-500/20 border-2 border-green-500 flex items-center justify-center">
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  </div>
                ) : step.status === 'current' ? (
                  <div className="w-8 h-8 rounded-full bg-purple-500/20 border-2 border-purple-500 flex items-center justify-center animate-pulse">
                    <Circle className="w-4 h-4 text-purple-400 fill-purple-400" />
                  </div>
                ) : (
                  <div className="w-8 h-8 rounded-full bg-gray-800 border-2 border-gray-700 flex items-center justify-center">
                    <Circle className="w-4 h-4 text-gray-600" />
                  </div>
                )}
              </div>
              
              {/* Content */}
              <div className="flex-1 pt-1">
                <h3 className={`text-lg font-semibold mb-2 ${
                  step.status === 'completed' ? 'text-green-400' :
                  step.status === 'current' ? 'text-white' :
                  'text-gray-500'
                }`}>
                  {step.title}
                </h3>
                <p className={`text-base ${
                  step.status === 'completed' ? 'text-gray-300' :
                  step.status === 'current' ? 'text-gray-200' :
                  'text-gray-600'
                }`}>
                  {step.description}
                </p>
              </div>
              
              {/* Arrow for next step */}
              {index < steps.length - 1 && step.status === 'current' && (
                <div className="flex items-center">
                  <ArrowDown className="w-6 h-6 text-purple-400 animate-bounce" />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
