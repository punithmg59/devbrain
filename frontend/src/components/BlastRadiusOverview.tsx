import { AlertTriangle, Layers, Route, Zap } from 'lucide-react'
import type { BlastRadius, BlastRadiusReport, BusinessImpactItem } from '../types/impact'

function categoryColor(cat: string): string {
  if (cat === 'critical') return 'text-red-400 border-red-800 bg-red-950/30'
  if (cat === 'high') return 'text-orange-400 border-orange-800 bg-orange-950/30'
  if (cat === 'medium') return 'text-yellow-400 border-yellow-800 bg-yellow-950/30'
  if (cat === 'low') return 'text-green-400 border-green-800 bg-green-950/30'
  return 'text-gray-400 border-gray-700 bg-gray-900/30'
}

interface Props {
  blast: BlastRadius
  report?: BlastRadiusReport | null
  businessItems?: BusinessImpactItem[]
}

export default function BlastRadiusOverview({ blast, report, businessItems }: Props) {
  const score = report?.blast_radius_score ?? blast.blast_radius_score ?? 0
  const category = report?.risk_category ?? blast.risk_category ?? 'safe'
  const metrics = [
    { label: 'Functions', value: report?.functions_impacted ?? blast.functions },
    { label: 'Files', value: report?.files_impacted ?? blast.files },
    { label: 'APIs', value: report?.apis_impacted ?? blast.api_routes },
    { label: 'Workflows', value: report?.workflows_impacted ?? blast.workflows_impacted ?? 0 },
    { label: 'Services', value: report?.services_impacted ?? blast.services_impacted ?? 0 },
    { label: 'Journeys', value: report?.journeys_impacted ?? blast.journeys_impacted ?? 0 },
  ]

  const criticalPaths =
    report?.critical_paths_impacted?.map((p) => p.name) ??
    blast.critical_paths_impacted ??
    []

  return (
    <section className="rounded-2xl border border-orange-500/20 bg-orange-950/10 p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Zap className="w-5 h-5 text-orange-400" />
        <h3 className="font-semibold">Blast radius intelligence</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className={`rounded-xl border p-4 text-center ${categoryColor(category)}`}>
          <p className="text-xs uppercase tracking-widest opacity-80">Blast radius score</p>
          <p className="text-5xl font-bold tabular-nums mt-1">{score}</p>
          <p className="text-sm mt-1 capitalize">{category} risk</p>
        </div>
        <div className="rounded-xl border border-white/10 p-4 space-y-2">
          <p className="text-xs uppercase text-gray-500">Deployment</p>
          <p className="text-lg font-medium capitalize">
            {(report?.deployment_risk ?? blast.deployment_risk ?? 'low').toUpperCase()}
          </p>
          <p className="text-xs text-gray-500">
            Users impacted:{' '}
            <span className="text-orange-300">
              {report?.estimated_users_impacted ?? blast.estimated_users_impacted ?? 'LOW'}
            </span>
          </p>
        </div>
        <div className="rounded-xl border border-white/10 p-4">
          <p className="text-xs uppercase text-gray-500 mb-2">Score breakdown</p>
          <ul className="text-xs space-y-1 text-gray-400">
            {(report?.score_breakdown ?? blast.score_breakdown ?? []).slice(0, 5).map((c) => (
              <li key={c.name}>
                {c.name}: {c.points}/{c.max_points}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-lg border border-white/10 p-3 text-center">
            <p className="text-xl font-bold tabular-nums">{m.value}</p>
            <p className="text-[10px] text-gray-500 uppercase">{m.label}</p>
          </div>
        ))}
      </div>

      {criticalPaths.length > 0 && (
        <div className="flex items-start gap-2">
          <Route className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs uppercase text-gray-500 mb-1">Critical paths impacted</p>
            <div className="flex flex-wrap gap-2">
              {criticalPaths.map((name) => (
                <span
                  key={name}
                  className="text-xs px-2 py-1 rounded border border-red-800/50 text-red-300"
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {(businessItems?.length ?? 0) > 0 && (
        <div className="flex items-start gap-2">
          <Layers className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs uppercase text-gray-500 mb-1">Business impact</p>
            <ul className="text-sm text-gray-300 space-y-1">
              {businessItems!.map((b, i) => (
                <li key={i} className="flex gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                  <span>
                    <strong>{b.impact_label}</strong> — {b.reason}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {report?.summary && (
        <p className="text-sm text-gray-400 border-t border-gray-800 pt-3">{report.summary}</p>
      )}
    </section>
  )
}
