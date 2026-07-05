import { GitBranch, Activity, Clock, CheckCircle } from 'lucide-react'

interface Props {
  repositoryName: string
  branch: string
  analysisStatus: 'analyzed' | 'analyzing' | 'not_analyzed'
  repositoryHealth: 'healthy' | 'warning' | 'critical'
  lastAnalysis: string
}

function getStatusColor(status: Props['analysisStatus']) {
  switch (status) {
    case 'analyzed':
      return 'text-green-400 bg-green-500/10 border-green-500/30'
    case 'analyzing':
      return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30'
    case 'not_analyzed':
      return 'text-gray-400 bg-gray-500/10 border-gray-500/30'
  }
}

function getHealthColor(health: Props['repositoryHealth']) {
  switch (health) {
    case 'healthy':
      return 'text-green-400'
    case 'warning':
      return 'text-yellow-400'
    case 'critical':
      return 'text-red-400'
  }
}

export default function RepositoryHeader({
  repositoryName,
  branch,
  analysisStatus,
  repositoryHealth,
  lastAnalysis
}: Props) {
  return (
    <div className="border-b border-gray-800 bg-gray-900/30 px-8 py-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          {/* Repository Info */}
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">{repositoryName}</h1>
            <div className="flex items-center gap-3 text-sm text-gray-400">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4" />
                <span>{branch}</span>
              </div>
              <span className="text-gray-600">•</span>
              <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium ${getStatusColor(analysisStatus)}`}>
                <Activity className="w-3 h-3" />
                <span className="capitalize">{analysisStatus.replace('_', ' ')}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Health & Status */}
        <div className="flex items-center gap-8">
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <Activity className="w-4 h-4" />
              Repository Health
            </div>
            <div className={`text-lg font-semibold ${getHealthColor(repositoryHealth)}`}>
              {repositoryHealth.charAt(0).toUpperCase() + repositoryHealth.slice(1)}
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <Clock className="w-4 h-4" />
              Last Analysis
            </div>
            <div className="text-lg font-semibold text-white">
              {lastAnalysis}
            </div>
          </div>

          {analysisStatus === 'analyzed' && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500/10 border border-green-500/30">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <span className="text-sm font-medium text-green-400">Ready</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
