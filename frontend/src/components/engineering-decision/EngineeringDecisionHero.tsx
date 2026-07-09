import { XCircle, AlertTriangle, CheckCircle, Server, FileCode } from 'lucide-react'

interface Props {
  verdict: 'SAFE' | 'MODERATE' | 'HIGH_RISK' | 'CRITICAL'
  targetName: string
  riskScore: number
  confidence: number
  blastRadius: number
  engineeringEffort: string
  whySentence: string
}

function getVerdictConfig(verdict: Props['verdict']) {
  switch (verdict) {
    case 'CRITICAL':
      return {
        icon: <XCircle className="w-8 h-8" />,
        color: 'text-red-400',
        bgColor: 'bg-red-950/20',
        borderColor: 'border-red-500/30',
        label: 'CRITICAL'
      }
    case 'HIGH_RISK':
      return {
        icon: <AlertTriangle className="w-8 h-8" />,
        color: 'text-orange-400',
        bgColor: 'bg-orange-950/20',
        borderColor: 'border-orange-500/30',
        label: 'HIGH RISK'
      }
    case 'MODERATE':
      return {
        icon: <AlertTriangle className="w-8 h-8" />,
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-950/20',
        borderColor: 'border-yellow-500/30',
        label: 'MODERATE'
      }
    case 'SAFE':
      return {
        icon: <CheckCircle className="w-8 h-8" />,
        color: 'text-green-400',
        bgColor: 'bg-green-950/20',
        borderColor: 'border-green-500/30',
        label: 'SAFE'
      }
  }
}

export default function EngineeringDecisionHero({
  verdict,
  targetName,
  riskScore,
  confidence,
  blastRadius,
  engineeringEffort,
  whySentence
}: Props) {
  const config = getVerdictConfig(verdict)

  return (
    <div className={`rounded-2xl border ${config.borderColor} ${config.bgColor} p-8`}>
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className={config.color}>
            {config.icon}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">
              {config.label}
            </h1>
            <p className="text-gray-400 mt-1">{targetName}</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-white">{Math.round(confidence * 100)}%</div>
          <div className="text-xs text-gray-500 uppercase tracking-wider">Confidence</div>
        </div>
      </div>

      {/* Risk Metrics Row */}
      <div className="flex gap-6 mb-4 text-sm">
        <div className="flex items-center gap-2 text-gray-400">
          <div className="w-2 h-2 rounded-full bg-purple-400" />
          <span>Risk: {riskScore}/100</span>
        </div>
        <div className="flex items-center gap-2 text-gray-400">
          <Server className="w-4 h-4" />
          <span>Blast Radius: {blastRadius} components</span>
        </div>
        <div className="flex items-center gap-2 text-gray-400">
          <FileCode className="w-4 h-4" />
          <span>Effort: {engineeringEffort}</span>
        </div>
      </div>

      {/* Why Sentence */}
      <div className="bg-black/20 rounded-lg p-4 border border-gray-700/30">
        <p className="text-gray-300 text-sm leading-relaxed">{whySentence}</p>
      </div>
    </div>
  )
}
