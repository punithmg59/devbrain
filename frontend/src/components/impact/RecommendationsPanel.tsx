import { Clock } from 'lucide-react'
import { Recommendation, ImpactHistoryItem } from '../../types/impact'

interface Props {
  recommendations: Recommendation[]
  history: ImpactHistoryItem[]
  isLoading: boolean
}

export function RecommendationsPanel({ recommendations, history, isLoading }: Props) {
  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return 'bg-red-400'
      case 'medium':
        return 'bg-amber-400'
      case 'low':
        return 'bg-gray-400'
      default:
        return 'bg-gray-400'
    }
  }

  const getPriorityBorderColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return 'border-red-500/40 bg-red-950/20'
      case 'medium':
        return 'border-amber-500/40 bg-amber-950/20'
      case 'low':
        return 'border-white/10 bg-white/5'
      default:
        return 'border-white/10 bg-white/5'
    }
  }

  const getRiskLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/30'
      case 'high':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
      case 'medium':
        return 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30'
      case 'low':
        return 'bg-green-500/20 text-green-400 border-green-500/30'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
    
    if (seconds < 60) return 'just now'
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
    return `${Math.floor(seconds / 86400)}d ago`
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Recommendations Section */}
      <div>
        <h3 className="text-[10px] uppercase tracking-wider text-gray-500 font-bold mb-3">
          Before You Change This
        </h3>

        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="p-4 rounded-lg bg-white/5 border border-white/10 animate-pulse">
                <div className="h-4 bg-white/10 rounded w-3/4 mb-2" />
                <div className="h-3 bg-white/10 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : recommendations.length === 0 ? (
          <p className="text-sm text-gray-500 italic">Run an analysis to see recommendations</p>
        ) : (
          <div className="space-y-3">
            {recommendations.map((rec, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border ${getPriorityBorderColor(rec.priority)}`}
              >
                <div className="flex items-start gap-2">
                  <div className={`w-2 h-2 rounded-full mt-1.5 ${getPriorityColor(rec.priority)}`} />
                  <div className="flex-1">
                    <h4 className="text-sm font-medium text-white">{rec.title}</h4>
                    <p className="text-xs text-white/60 mt-1">{rec.body}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="h-px bg-white/10" />

      {/* History Section */}
      <div>
        <h3 className="text-[10px] uppercase tracking-wider text-gray-500 font-bold mb-3">
          Recent Analyses
        </h3>

        {history.length === 0 ? (
          <p className="text-sm text-gray-500">No previous analyses</p>
        ) : (
          <div className="space-y-2">
            {history.slice(0, 5).map((item) => (
              <div
                key={item.id}
                className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{item.node_name}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${getRiskLevelColor(item.risk_level)}`}>
                      {item.node_type}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${getRiskLevelColor(item.risk_level)}`}>
                      {item.risk_level}
                    </span>
                    <div className="flex items-center gap-1 text-gray-500">
                      <Clock className="w-3 h-3" />
                      <span className="text-[10px]">{formatTimeAgo(item.created_at)}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
