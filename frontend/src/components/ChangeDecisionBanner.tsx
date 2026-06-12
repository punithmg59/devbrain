import { CheckCircle2, ShieldAlert, XCircle } from 'lucide-react'
import type { ChangeRecommendation } from '../types/impact'

export default function ChangeDecisionBanner({
  recommendation,
  riskScore,
}: {
  recommendation: ChangeRecommendation
  riskScore: number
}) {
  const { should_proceed, label, decision } = recommendation

  if (decision === 'block') {
    return (
      <div className="rounded-2xl border border-red-500/40 bg-red-950/30 p-6 flex gap-4">
        <XCircle className="w-10 h-10 text-red-400 shrink-0" />
        <div>
          <p className="text-xs uppercase tracking-widest text-red-400 mb-1">
            Recommendation
          </p>
          <h3 className="text-xl font-bold text-white">Do not ship this change yet</h3>
          <p className="text-red-200/80 mt-2 text-sm">{label}</p>
          <p className="text-xs text-red-400/60 mt-2">Risk score {riskScore}/100</p>
        </div>
      </div>
    )
  }

  if (!should_proceed) {
    return (
      <div className="rounded-2xl border border-amber-500/40 bg-amber-950/20 p-6 flex gap-4">
        <ShieldAlert className="w-10 h-10 text-amber-400 shrink-0" />
        <div>
          <p className="text-xs uppercase tracking-widest text-amber-400 mb-1">
            Requires review
          </p>
          <h3 className="text-xl font-bold text-white">Proceed only after review</h3>
          <p className="text-amber-200/80 mt-2 text-sm">{label}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-6 flex gap-4">
      <CheckCircle2 className="w-10 h-10 text-emerald-400 shrink-0" />
      <div>
        <p className="text-xs uppercase tracking-widest text-emerald-400 mb-1">
          Clear to proceed
        </p>
        <h3 className="text-xl font-bold text-white">Change is acceptable with controls</h3>
        <p className="text-emerald-200/80 mt-2 text-sm">{label}</p>
      </div>
    </div>
  )
}
