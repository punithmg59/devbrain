import type { RiskScoreBreakdown, ConfidenceBreakdown } from '../types/impact'

export function RiskBreakdownCard({ breakdown }: { breakdown: RiskScoreBreakdown }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
      <div className="flex justify-between items-baseline mb-4">
        <h3 className="font-semibold text-sm">Risk score breakdown</h3>
        <span className="text-2xl font-bold tabular-nums">
          {breakdown.total}
          <span className="text-sm text-gray-500 font-normal">/100</span>
        </span>
      </div>
      <ul className="space-y-2">
        {breakdown.components.map((c) => (
          <li key={c.name}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-400">{c.name}</span>
              <span className="text-gray-300">
                {c.points}/{c.max_points}
              </span>
            </div>
            <div className="h-1 bg-gray-800 rounded overflow-hidden">
              <div
                className="h-full bg-purple-500 rounded"
                style={{ width: `${(c.points / Math.max(c.max_points, 1)) * 100}%` }}
              />
            </div>
            <p className="text-[10px] text-gray-600 mt-0.5">{c.evidence}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ConfidenceBreakdownCard({
  breakdown,
}: {
  breakdown: ConfidenceBreakdown
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
      <div className="flex justify-between items-baseline mb-4">
        <h3 className="font-semibold text-sm">Confidence breakdown</h3>
        <span className="text-2xl font-bold text-emerald-400 tabular-nums">
          {Math.round(breakdown.total * 100)}%
        </span>
      </div>
      <ul className="space-y-2">
        {breakdown.components.map((c) => (
          <li key={c.name} className="flex justify-between text-xs">
            <span className="text-gray-500">{c.name}</span>
            <span className="text-gray-400">{c.evidence}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
