import type { SmartResolvedEntity } from '../types/resolver'

interface Props {
  candidates: SmartResolvedEntity[]
  resolutionMs: number
  onSelect: (entity: SmartResolvedEntity) => void
  onAnalyzeTop: () => void
}

export default function ResolverCandidatesPanel({
  candidates,
  resolutionMs,
  onSelect,
  onAnalyzeTop,
}: Props) {
  if (candidates.length === 0) return null

  const top = candidates[0]

  return (
    <div className="max-w-3xl mx-auto px-6 mt-6 text-left">
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-gray-400">
            Smart Resolver · {resolutionMs}ms · {candidates.length} matches
          </p>
          <button
            type="button"
            onClick={onAnalyzeTop}
            className="text-xs px-3 py-1.5 bg-purple-600 rounded-lg hover:bg-purple-500"
          >
            Analyze top match
          </button>
        </div>

        <p className="text-xs text-gray-500 mb-3">
          Resolved target: <span className="text-white font-medium">{top.name}</span>
          {' · '}
          <span className="text-emerald-400">{top.confidence}% confidence</span>
        </p>

        <ul className="space-y-2">
          {candidates.map((c, i) => (
            <li key={`${c.entity_id}-${i}`}>
              <button
                type="button"
                onClick={() => onSelect(c)}
                className="w-full p-3 rounded-xl border border-gray-800 hover:border-purple-600/50 hover:bg-white/[0.03] text-left transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-sm">{c.name}</span>
                  <span className="text-xs text-emerald-400 tabular-nums shrink-0">
                    {c.confidence}%
                  </span>
                </div>
                <p className="text-[10px] text-gray-600 mt-1 uppercase">{c.entity_type}</p>
                <p className="text-xs text-gray-500 mt-2">{c.reason}</p>
                {c.workflow_name && (
                  <p className="text-[10px] text-purple-400 mt-1">
                    Workflow: {c.workflow_name}
                  </p>
                )}
                {c.route_path && (
                  <p className="text-[10px] text-green-500/80 mt-1 font-mono">
                    {c.http_method} {c.route_path}
                  </p>
                )}
                {c.graph_connections.length > 0 && (
                  <p className="text-[10px] text-gray-600 mt-1">
                    Graph: {c.graph_connections.slice(0, 4).join(', ')}
                  </p>
                )}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
