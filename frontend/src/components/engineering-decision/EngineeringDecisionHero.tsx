import { XCircle, AlertTriangle, CheckCircle, Clock, Target, TrendingUp, Layers } from 'lucide-react'

interface Props {
  verdict: 'DO_NOT_DELETE' | 'HIGH_RISK' | 'PROCEED_WITH_CAUTION' | 'SAFE_TO_CHANGE'
  targetName: string
  riskScore: number
  confidence: number
  impactCount: number
  analysisTime: string
  summary: string
}

function getVerdictConfig(verdict: Props['verdict']) {
  switch (verdict) {
    case 'DO_NOT_DELETE':
      return {
        icon: <XCircle className="w-12 h-12" />,
        color: 'text-red-400',
        bgColor: 'bg-red-950/20',
        borderColor: 'border-red-500/30',
        iconBg: 'bg-red-500/10'
      }
    case 'HIGH_RISK':
      return {
        icon: <AlertTriangle className="w-12 h-12" />,
        color: 'text-orange-400',
        bgColor: 'bg-orange-950/20',
        borderColor: 'border-orange-500/30',
        iconBg: 'bg-orange-500/10'
      }
    case 'PROCEED_WITH_CAUTION':
      return {
        icon: <AlertTriangle className="w-12 h-12" />,
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-950/20',
        borderColor: 'border-yellow-500/30',
        iconBg: 'bg-yellow-500/10'
      }
    case 'SAFE_TO_CHANGE':
      return {
        icon: <CheckCircle className="w-12 h-12" />,
        color: 'text-green-400',
        bgColor: 'bg-green-950/20',
        borderColor: 'border-green-500/30',
        iconBg: 'bg-green-500/10'
      }
  }
}

export default function EngineeringDecisionHero({
  verdict,
  targetName,
  riskScore,
  confidence,
  impactCount,
  analysisTime,
  summary
}: Props) {
  const config = getVerdictConfig(verdict)

  return (
    <div className={`rounded-2xl border ${config.borderColor} ${config.bgColor} p-8 mb-8`}>
      <div className="flex items-start justify-between mb-8">
        <div className="flex items-center gap-6">
          <div className={`p-4 rounded-2xl ${config.iconBg} ${config.color}`}>
            {config.icon}
          </div>
          <div>
            <h1 className="text-4xl font-bold text-white mb-2 tracking-tight">{verdict.replace(/_/g, ' ')}</h1>
            <p className="text-xl text-gray-400 font-medium">{targetName}</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-6xl font-bold text-white tabular-nums">{riskScore}</div>
          <div className="text-sm text-gray-400 uppercase tracking-wider">Risk Score</div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8 pt-6 border-t border-gray-700/50">
        <div>
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <Target className="w-4 h-4" />
            Confidence
          </div>
          <div className="text-3xl font-semibold text-white tabular-nums">
            {Math.round(confidence * 100)}%
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <TrendingUp className="w-4 h-4" />
            Impact
          </div>
          <div className="text-3xl font-semibold text-white">
            {impactCount}
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <Clock className="w-4 h-4" />
            Analysis Time
          </div>
          <div className="text-3xl font-semibold text-white tabular-nums">
            {analysisTime}s
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <Layers className="w-4 h-4" />
            Components
          </div>
          <div className="text-3xl font-semibold text-white">
            {impactCount}
          </div>
        </div>
      </div>

      <div className="bg-gray-900/50 rounded-xl p-5 border border-gray-700/50">
        <p className="text-lg text-gray-200 leading-relaxed">{summary}</p>
      </div>
    </div>
  )
}
