import { useState, useEffect } from 'react'
import { Play, AlertTriangle, Shield, CheckCircle, XCircle } from 'lucide-react'
import { repoService } from '../../services/repoService'
import type { SimulationResult, ChangeType } from '../../types/simulation'
import SimulationTimeline from './SimulationTimeline'
import ImpactSummary from './ImpactSummary'
import DependencyPathVisualization from './DependencyPathVisualization'

interface Props {
  repoId: string
  targetName: string
  changeType?: ChangeType
  targetType?: string
}

export default function SimulationUI({ repoId, targetName, changeType = 'delete', targetType }: Props) {
  const [simulation, setSimulation] = useState<SimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedChangeType, setSelectedChangeType] = useState<ChangeType>(changeType)

  useEffect(() => {
    if (targetName) {
      runSimulation()
    }
  }, [targetName, selectedChangeType])

  const runSimulation = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await repoService.simulateChange({
        repo_id: repoId,
        change_type: selectedChangeType,
        target_name: targetName,
        target_type: targetType,
        max_depth: 5
      })
      setSimulation(result)
    } catch (err) {
      setError('Failed to run simulation')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getRiskLevelIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical':
        return <XCircle className="w-6 h-6 text-red-400" />
      case 'high':
        return <AlertTriangle className="w-6 h-6 text-orange-400" />
      case 'moderate':
        return <Shield className="w-6 h-6 text-yellow-400" />
      case 'safe':
        return <CheckCircle className="w-6 h-6 text-green-400" />
      default:
        return <Shield className="w-6 h-6 text-gray-400" />
    }
  }

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical':
        return 'border-red-500/50 bg-red-950/30'
      case 'high':
        return 'border-orange-500/50 bg-orange-950/30'
      case 'moderate':
        return 'border-yellow-500/50 bg-yellow-950/30'
      case 'safe':
        return 'border-green-500/50 bg-green-950/30'
      default:
        return 'border-gray-500/50 bg-gray-950/30'
    }
  }

  const changeTypes: { value: ChangeType; label: string }[] = [
    { value: 'delete', label: 'Delete' },
    { value: 'rename', label: 'Rename' },
    { value: 'move', label: 'Move' },
    { value: 'extract', label: 'Extract' },
    { value: 'add', label: 'Add' }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">Change Simulation</h2>
          <p className="text-sm text-gray-500 mt-1">
            {selectedChangeType} {targetName}
          </p>
        </div>
        <button
          onClick={runSimulation}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Simulating
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Run Simulation
            </>
          )}
        </button>
      </div>

      {/* Change Type Selector */}
      <div className="flex flex-wrap gap-2">
        {changeTypes.map((type) => (
          <button
            key={type.value}
            onClick={() => setSelectedChangeType(type.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedChangeType === type.value
                ? 'bg-purple-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {type.label}
          </button>
        ))}
      </div>

      {/* Error State */}
      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-950/20 p-6 text-sm text-red-200">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/30 p-12 text-center text-gray-500">
          Running simulation...
        </div>
      )}

      {/* Simulation Results */}
      {simulation && !loading && (
        <div className="space-y-6 animate-fade-in">
          {/* Risk Level Card */}
          <div className={`rounded-2xl border p-6 ${getRiskLevelColor(simulation.risk_level)}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {getRiskLevelIcon(simulation.risk_level)}
                <div>
                  <h3 className="text-xl font-semibold text-white capitalize">
                    {simulation.risk_level} Risk
                  </h3>
                  <p className="text-sm text-gray-400 mt-1">
                    Confidence: {Math.round(simulation.confidence * 100)}%
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-white">
                  {simulation.impact_metrics.estimated_blast_radius}
                </div>
                <div className="text-xs text-gray-500 uppercase tracking-wider">
                  Affected Components
                </div>
              </div>
            </div>
          </div>

          {/* Impact Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
              <div className="text-2xl font-bold text-green-400">
                {simulation.impact_metrics.affected_apis}
              </div>
              <div className="text-xs text-gray-500 uppercase tracking-wider">APIs</div>
            </div>
            <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
              <div className="text-2xl font-bold text-blue-400">
                {simulation.impact_metrics.affected_services}
              </div>
              <div className="text-xs text-gray-500 uppercase tracking-wider">Services</div>
            </div>
            <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
              <div className="text-2xl font-bold text-purple-400">
                {simulation.impact_metrics.affected_classes}
              </div>
              <div className="text-xs text-gray-500 uppercase tracking-wider">Classes</div>
            </div>
            <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
              <div className="text-2xl font-bold text-yellow-400">
                {simulation.impact_metrics.critical_dependency_chains}
              </div>
              <div className="text-xs text-gray-500 uppercase tracking-wider">Critical Chains</div>
            </div>
          </div>

          {/* Timeline */}
          {simulation.timeline.length > 0 && (
            <SimulationTimeline steps={simulation.timeline} changeType={simulation.change_type} />
          )}

          {/* Impact Summary */}
          <ImpactSummary impactSummary={simulation.impact_summary} />

          {/* Dependency Paths */}
          {simulation.cascade_chains.length > 0 && (
            <DependencyPathVisualization cascadeChains={simulation.cascade_chains} />
          )}
        </div>
      )}
    </div>
  )
}
