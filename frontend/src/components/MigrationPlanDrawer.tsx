import { useState, useEffect } from 'react'
import { X, Clock, CheckCircle, Circle, ChevronRight, ChevronDown } from 'lucide-react'
import { repoService } from '../services/repoService'

interface MigrationStep {
  step: number
  title: string
  description: string
  actions: string[]
  estimated_time: string
  status: 'pending' | 'in_progress' | 'completed'
}

interface MigrationPlanData {
  target_name: string
  target_type: string
  change_type: string
  overall_criticality: string
  total_references: number
  steps: MigrationStep[]
  estimated_total_time: number
}

interface Props {
  isOpen: boolean
  onClose: () => void
  repoId: string
  targetName: string
  targetType?: string
  changeType?: string
}

export default function MigrationPlanDrawer({ isOpen, onClose, repoId, targetName, targetType, changeType }: Props) {
  const [data, setData] = useState<MigrationPlanData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (isOpen && repoId && targetName) {
      loadMigrationPlan()
    }
  }, [isOpen, repoId, targetName])

  const loadMigrationPlan = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await repoService.generateMigrationPlan(repoId, undefined, targetName, targetType, changeType)
      setData(result)
      // Expand all steps by default
      setExpandedSteps(new Set(result.steps.map((s: MigrationStep) => s.step)))
    } catch (err) {
      setError('Failed to generate migration plan')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const toggleStep = (stepNumber: number) => {
    setExpandedSteps(prev => {
      const next = new Set(prev)
      if (next.has(stepNumber)) {
        next.delete(stepNumber)
      } else {
        next.add(stepNumber)
      }
      return next
    })
  }

  const toggleStepStatus = (stepNumber: number) => {
    if (!data) return
    setData(prev => {
      if (!prev) return prev
      return {
        ...prev,
        steps: prev.steps.map(step => 
          step.step === stepNumber 
            ? { 
                ...step, 
                status: step.status === 'completed' ? 'pending' : 
                        step.status === 'pending' ? 'in_progress' : 'completed' 
              }
            : step
        )
      }
    })
  }

  const getCriticalityColor = (criticality: string) => {
    switch (criticality.toLowerCase()) {
      case 'critical': return 'text-red-400 bg-red-500/10 border-red-500/20'
      case 'high': return 'text-orange-400 bg-orange-500/10 border-orange-500/20'
      case 'medium': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
      case 'low': return 'text-green-400 bg-green-500/10 border-green-500/20'
      default: return 'text-gray-400 bg-gray-500/10 border-gray-500/20'
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Drawer */}
      <div className="relative ml-auto h-full w-[700px] bg-[#09090b] border-l border-gray-800 shadow-2xl flex flex-col animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div>
            <h2 className="text-xl font-semibold text-white">Migration Plan</h2>
            {data && (
              <p className="text-sm text-gray-500 mt-1">
                {data.target_name} • {data.total_references} references
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              Generating migration plan...
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-red-400">
              {error}
            </div>
          ) : data ? (
            <div className="p-6 space-y-6">
              {/* Summary */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-2xl font-bold text-white">{data.steps.length}</div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider">Steps</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-2xl font-bold text-white">{Math.round(data.estimated_total_time)}h</div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider">Est. Time</div>
                </div>
              </div>

              {/* Criticality Badge */}
              <div className={`px-3 py-2 rounded-lg border text-sm font-medium ${getCriticalityColor(data.overall_criticality)}`}>
                {data.overall_criticality} Criticality
              </div>

              {/* Steps */}
              <div className="space-y-3">
                {data.steps.map((step) => (
                  <div
                    key={step.step}
                    className="bg-gray-900/30 rounded-lg border border-gray-800 overflow-hidden"
                  >
                    {/* Step Header */}
                    <button
                      onClick={() => toggleStep(step.step)}
                      className="w-full flex items-center justify-between p-4 hover:bg-gray-800/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            toggleStepStatus(step.step)
                          }}
                          className="p-1 rounded hover:bg-gray-700 transition-colors"
                        >
                          {step.status === 'completed' ? (
                            <CheckCircle className="w-5 h-5 text-green-400" />
                          ) : step.status === 'in_progress' ? (
                            <Circle className="w-5 h-5 text-yellow-400 fill-yellow-400/20" />
                          ) : (
                            <Circle className="w-5 h-5 text-gray-500" />
                          )}
                        </button>
                        <div className="text-left">
                          <div className="font-medium text-white">Step {step.step}: {step.title}</div>
                          <div className="text-sm text-gray-500">{step.description}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          <Clock className="w-3 h-3" />
                          {step.estimated_time}
                        </div>
                        {expandedSteps.has(step.step) ? (
                          <ChevronDown className="w-4 h-4 text-gray-500" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-500" />
                        )}
                      </div>
                    </button>

                    {/* Step Details */}
                    {expandedSteps.has(step.step) && (
                      <div className="px-4 pb-4 pt-2 border-t border-gray-800">
                        <div className="space-y-2">
                          {step.actions.map((action, idx) => (
                            <div
                              key={idx}
                              className="flex items-start gap-2 text-sm text-gray-400"
                            >
                              <ChevronRight className="w-4 h-4 mt-0.5 shrink-0" />
                              <span>{action}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
