import { useState } from 'react'
import { Link } from 'react-router-dom'
import { submitWorkflowFeedback } from '../services/workflowService'
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  Code2,
  Copy,
  Database,
  FileCode2,
  GitBranch,
  Globe,
  Network,
  Rocket,
  Share2,
  TestTube2,
  Users,
} from 'lucide-react'
import type { ExactDependencyItem } from '../types/impact'
import RiskBadge from './RiskBadge'
import NodeTypeBadge from './NodeTypeBadge'
import ImpactDependencyGraph from './ImpactDependencyGraph'
import ChangeDecisionBanner from './ChangeDecisionBanner'
import BlastRadiusOverview from './BlastRadiusOverview'
import { RiskBreakdownCard, ConfidenceBreakdownCard } from './ScoreBreakdownCard'
import type { ImpactResult } from '../types/impact'

function riskTierLabel(score100: number): 'low' | 'medium' | 'high' | 'critical' {
  if (score100 <= 40) return 'low'
  if (score100 <= 60) return 'medium'
  if (score100 <= 80) return 'high'
  return 'critical'
}

function priorityColor(p: string): string {
  if (p === 'critical') return 'text-red-400 border-red-800 bg-red-950/30'
  if (p === 'high') return 'text-orange-400 border-orange-800 bg-orange-950/30'
  return 'text-yellow-400 border-yellow-800 bg-yellow-950/30'
}

interface Props {
  result: ImpactResult
  repoId: string
  onCopyReport: () => void
  onShare: () => void
}

function WorkflowFeedbackButtons({
  repoId,
  query,
  workflowId,
}: {
  repoId: string
  query: string
  workflowId: string
}) {
  const [status, setStatus] = useState<'idle' | 'sent' | 'error'>('idle')
  const [message, setMessage] = useState('')

  async function send(accepted: boolean) {
    try {
      const res = await submitWorkflowFeedback(repoId, {
        query,
        workflow_id: workflowId,
        accepted,
        rejected: !accepted,
      })
      setMessage(res.message)
      setStatus('sent')
    } catch {
      setStatus('error')
      setMessage('Could not save feedback')
    }
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={() => send(true)}
        disabled={status === 'sent'}
        className="text-xs px-2 py-1 rounded border border-green-800 text-green-400 hover:bg-green-950/30 disabled:opacity-50"
      >
        ✓ Accurate
      </button>
      <button
        type="button"
        onClick={() => send(false)}
        disabled={status === 'sent'}
        className="text-xs px-2 py-1 rounded border border-red-800 text-red-400 hover:bg-red-950/30 disabled:opacity-50"
      >
        ✗ Incorrect
      </button>
      {message && (
        <span className="text-[10px] text-gray-500">{message}</span>
      )}
    </div>
  )
}

import type { ExactDependencies } from '../types/impact'

function DepList({ title, icon, items, color }: {
  title: string
  icon: React.ReactNode
  items: ExactDependencyItem[]
  color: string
}) {
  if (items.length === 0) return null
  return (
    <div className="rounded-xl border border-white/10 bg-gray-900/40 p-4">
      <div className={`flex items-center gap-2 mb-3 ${color}`}>
        {icon}
        <span className="text-xs font-semibold uppercase tracking-wider">{title}</span>
        <span className="ml-auto text-xs text-gray-600">{items.length} nodes</span>
      </div>
      <ul className="space-y-1.5 max-h-48 overflow-y-auto">
        {items.map((item) => (
          <li key={item.id} className="flex items-start gap-2 text-xs group">
            <ArrowRight className="w-3 h-3 mt-0.5 text-gray-600 shrink-0 group-hover:text-gray-400" />
            <div className="min-w-0">
              <span className="font-medium text-gray-200">{item.name}</span>
              <span className="ml-1.5 px-1 py-0.5 rounded text-[10px] bg-gray-800 text-gray-500">
                {item.node_type}
              </span>
              {item.file_path && (
                <p className="text-[10px] text-gray-600 truncate mt-0.5 font-mono">{item.file_path}</p>
              )}
            </div>
            <span className="ml-auto shrink-0 text-[10px] text-gray-600 tabular-nums">
              {Math.round(item.confidence * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function ExactDependenciesPanel({ deps }: { deps: ExactDependencies | null }) {
  if (!deps) {
    return (
      <div className="rounded-2xl border border-dashed border-gray-700 p-10 text-center text-gray-500 text-sm">
        No dependency intelligence available. Run an impact analysis to populate this.
      </div>
    )
  }

  const totalDeps =
    deps.level_1_direct.length +
    deps.level_1_incoming.length +
    deps.level_2_indirect.length +
    deps.level_3_workflow.length

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 rounded-2xl border border-purple-500/20 bg-purple-950/10 p-4">
        <Network className="w-5 h-5 text-purple-400 shrink-0" />
        <div>
          <p className="font-semibold text-sm">Dependency Intelligence</p>
          <p className="text-xs text-gray-500">
            {totalDeps} total graph dependencies · {deps.file_dependencies.length} files · {deps.api_dependencies.length} API routes · {deps.database_dependencies.length} DB deps
          </p>
        </div>
      </div>

      {/* L1 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <DepList
          title="L1 · Directly Calls"
          icon={<ArrowRight className="w-4 h-4" />}
          items={deps.level_1_direct}
          color="text-red-400"
        />
        <DepList
          title="L1 · Called By"
          icon={<ArrowRight className="w-4 h-4 rotate-180" />}
          items={deps.level_1_incoming}
          color="text-orange-400"
        />
      </div>

      {/* L2 */}
      <DepList
        title="L2 · Indirect Dependencies"
        icon={<Network className="w-4 h-4" />}
        items={deps.level_2_indirect}
        color="text-yellow-400"
      />

      {/* L3 */}
      <DepList
        title="L3 · Business Workflow Dependencies"
        icon={<GitBranch className="w-4 h-4" />}
        items={deps.level_3_workflow}
        color="text-cyan-400"
      />

      {/* Specialised */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <DepList
          title="API Dependencies"
          icon={<Globe className="w-4 h-4" />}
          items={deps.api_dependencies}
          color="text-green-400"
        />
        <DepList
          title="Database Dependencies"
          icon={<Database className="w-4 h-4" />}
          items={deps.database_dependencies}
          color="text-blue-400"
        />
      </div>

      {/* File Dependencies */}
      {deps.file_dependencies.length > 0 && (
        <div className="rounded-xl border border-white/10 bg-gray-900/40 p-4">
          <div className="flex items-center gap-2 mb-3 text-gray-400">
            <FileCode2 className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Files Impacted</span>
            <span className="ml-auto text-xs text-gray-600">{deps.file_dependencies.length}</span>
          </div>
          <ul className="space-y-1 max-h-40 overflow-y-auto">
            {deps.file_dependencies.map((fp) => (
              <li key={fp} className="text-xs font-mono text-gray-400 truncate hover:text-gray-200 transition-colors">
                {fp}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function ImpactReportView({
  result,
  repoId,
  onCopyReport,
  onShare,
}: Props) {
  const [activeTab, setActiveTab] = useState<
    'overview' | 'deps' | 'graph' | 'tests' | 'deploy'
  >('overview')

  const badgeLevel = riskTierLabel(result.risk_score_100 ?? 0)
  const br = result.blast_radius

  return (
    <section className="max-w-6xl mx-auto px-6 pb-20 space-y-6">
      {result.warning && (
        <div className="p-4 rounded-xl border border-yellow-700/50 bg-yellow-950/20 text-yellow-200 text-sm flex gap-2">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          {result.warning}
        </div>
      )}

      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          onClick={onCopyReport}
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 border border-gray-700 rounded-lg hover:bg-white/5"
        >
          <Copy className="w-4 h-4" />
          Copy report
        </button>
        <button
          type="button"
          onClick={onShare}
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 border border-gray-700 rounded-lg hover:bg-white/5"
        >
          <Share2 className="w-4 h-4" />
          Share
        </button>
      </div>

      <ChangeDecisionBanner
        recommendation={result.change_recommendation}
        riskScore={result.risk_score_100}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-gray-900/80 to-transparent p-6">
            <p className="text-xs uppercase tracking-widest text-gray-500 mb-2">
              Executive summary · {result.scenario} scenario
            </p>
            <p className="text-lg text-white leading-relaxed">
              {result.executive_summary}
            </p>
          </div>
          <div className="rounded-2xl border border-purple-500/20 bg-purple-950/10 p-5">
            <p className="text-xs uppercase text-purple-400 mb-2">Why this matters</p>
            <p className="text-gray-300 text-sm leading-relaxed">{result.why_this_matters}</p>
          </div>
        </div>
        <div className="space-y-4">
          <div className="rounded-2xl border border-white/10 p-5 text-center">
            <RiskBadge level={badgeLevel} size="lg" />
            <p className="text-4xl font-bold mt-3 tabular-nums">{result.risk_score_100}</p>
            <p className="text-xs text-gray-500">/100 risk</p>
          </div>
          <ConfidenceBreakdownCard breakdown={result.confidence_breakdown} />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Nodes', value: br.total_nodes },
          { label: 'APIs', value: br.api_routes },
          { label: 'Files', value: br.files },
          { label: 'Verified edges', value: br.verified_edges },
        ].map((m) => (
          <div key={m.label} className="rounded-xl border border-white/10 p-4 text-center">
            <p className="text-2xl font-bold">{m.value}</p>
            <p className="text-xs text-gray-500">{m.label}</p>
          </div>
        ))}
      </div>

      <RiskBreakdownCard breakdown={result.risk_score_breakdown} />

      <BlastRadiusOverview
        blast={result.blast_radius}
        report={result.blast_radius_report}
        businessItems={result.business_impact_items}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-white/10 p-5">
          <div className="flex items-center gap-2 mb-3">
            <Building2 className="w-4 h-4 text-purple-400" />
            <h3 className="font-semibold text-sm">Business impact</h3>
          </div>
          <ul className="space-y-2 text-sm text-gray-300">
            {result.business_impact.map((l, i) => (
              <li key={i}>• {l}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-2xl border border-white/10 p-5">
          <div className="flex items-center gap-2 mb-3">
            <Code2 className="w-4 h-4 text-blue-400" />
            <h3 className="font-semibold text-sm">Engineering impact</h3>
          </div>
          <ul className="space-y-2 text-sm text-gray-300">
            {(result.engineering_impact.length ? result.engineering_impact : result.developer_impact).map(
              (l, i) => (
                <li key={i}>• {l}</li>
              )
            )}
          </ul>
        </div>
      </div>

      {(result.primary_workflow || result.workflow_impact.length > 0) && (
        <div className="rounded-2xl border border-cyan-500/20 bg-cyan-950/10 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-cyan-400" />
            <h3 className="font-semibold">Workflow intelligence</h3>
          </div>

          {result.primary_workflow && (
            <div className="p-4 rounded-xl border border-cyan-800/40 bg-gray-900/40">
              <p className="text-xs uppercase text-cyan-400 mb-1">Primary workflow</p>
              <p className="text-lg font-semibold">{result.primary_workflow.name}</p>
              <p className="text-sm text-gray-400 mt-1">
                Confidence:{' '}
                <span className="text-cyan-300 tabular-nums">
                  {Math.round(
                    (result.primary_workflow.confidence_percent ??
                      result.primary_workflow.confidence * 100) as number
                  )}
                  %
                </span>
                {result.primary_workflow.service_name && (
                  <> · Service: {result.primary_workflow.service_name}</>
                )}
              </p>
              {result.primary_workflow.id && (
                <WorkflowFeedbackButtons
                  repoId={repoId}
                  query={result.query}
                  workflowId={result.primary_workflow.id}
                />
              )}
            </div>
          )}

          {(result.affected_journeys?.length ?? 0) > 0 && (
            <div>
              <p className="text-xs uppercase text-gray-500 mb-2">Affected user journeys</p>
              <div className="flex flex-wrap gap-2">
                {result.affected_journeys!.map((j) => (
                  <span
                    key={j}
                    className="text-xs px-2 py-1 rounded-full border border-purple-800/50 text-purple-300"
                  >
                    {j}
                  </span>
                ))}
              </div>
            </div>
          )}

          {(result.affected_systems?.length ?? 0) > 0 && (
            <div>
              <p className="text-xs uppercase text-gray-500 mb-2">Affected services</p>
              <div className="flex flex-wrap gap-2">
                {result.affected_systems.map((s) => (
                  <span
                    key={s}
                    className="text-xs px-2 py-1 rounded-full border border-blue-800/50 text-blue-300"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.workflow_evidence && result.workflow_evidence.length > 0 && (
            <div>
              <p className="text-xs uppercase text-gray-500 mb-2">Workflow evidence</p>
              {result.workflow_evidence.map((ev) => (
                <p
                  key={ev.workflow_id}
                  className="text-sm text-gray-300 font-mono break-all"
                >
                  {ev.chain_summary}{' '}
                  <span className="text-cyan-500">
                    ({ev.confidence_percent}% confidence)
                  </span>
                </p>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {result.workflow_impact.map((wf) => (
              <div
                key={wf.workflow_id}
                className="p-3 rounded-xl bg-gray-900/50 border border-gray-800"
              >
                <div className="flex justify-between items-start gap-2">
                  <p className="font-medium text-sm">{wf.workflow_name}</p>
                  {wf.severity && (
                    <span className="text-[10px] uppercase text-orange-400">
                      {wf.severity}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">{wf.user_impact}</p>
                {wf.service_name && (
                  <p className="text-[10px] text-blue-400 mt-1">Service: {wf.service_name}</p>
                )}
                {wf.evidence_chain && (
                  <p className="text-[10px] text-gray-500 mt-2 font-mono">{wf.evidence_chain}</p>
                )}
                {wf.evidence_nodes.length > 0 && (
                  <p className="text-[10px] text-gray-600 mt-1">
                    Nodes: {wf.evidence_nodes.join(' → ')}
                  </p>
                )}
                {wf.affected_apis && wf.affected_apis.length > 0 && (
                  <p className="text-[10px] text-gray-600 mt-1">
                    APIs: {wf.affected_apis.slice(0, 4).join(', ')}
                  </p>
                )}
                {wf.recommended_tests && wf.recommended_tests.length > 0 && (
                  <p className="text-[10px] text-amber-600/80 mt-1">
                    Tests: {wf.recommended_tests.join(', ')}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {result.user_impact.length > 0 && (
        <div className="rounded-2xl border border-white/10 p-5">
          <div className="flex items-center gap-2 mb-3">
            <Users className="w-4 h-4 text-pink-400" />
            <h3 className="font-semibold text-sm">User impact</h3>
          </div>
          <ul className="space-y-2 text-sm text-gray-300">
            {result.user_impact.map((u, i) => (
              <li key={i}>• {u}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-2xl border border-purple-800/30 bg-purple-950/10 p-5">
        <p className="text-xs uppercase text-purple-400 mb-2">Staff engineer recommendation</p>
        <p className="text-gray-200 leading-relaxed">{result.staff_engineer_recommendation}</p>
        <p className="text-xs text-gray-600 mt-3 border-t border-gray-800 pt-3">
          {result.risk_analysis}
        </p>
      </div>

      <div className="flex gap-2 border-b border-gray-800 pb-2 flex-wrap">
        {(
          [
            ['overview', 'Functions & files'],
            ['deps', 'Dependency Intel'],
            ['graph', 'Blast radius'],
            ['tests', 'Test plan'],
            ['deploy', 'Deploy'],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={`px-4 py-2 text-sm rounded-lg ${
              activeTab === key ? 'bg-white text-black' : 'text-gray-500'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'graph' && <ImpactDependencyGraph graph={result.graph} />}

      {activeTab === 'deps' && (
        <ExactDependenciesPanel deps={result.exact_dependencies ?? null} />
      )}

      {activeTab === 'tests' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-2xl border border-white/10 p-5">
            <div className="flex items-center gap-2 mb-4">
              <TestTube2 className="w-5 h-5 text-amber-400" />
              <h3 className="font-semibold">Recommended tests</h3>
            </div>
            <ul className="space-y-3">
              {result.recommended_tests.map((t, i) => (
                <li key={i} className={`p-3 rounded-xl border text-sm ${priorityColor(t.priority)}`}>
                  <div className="flex justify-between">
                    <span className="font-medium">{t.title}</span>
                    <span className="text-[10px] uppercase">{t.priority}</span>
                  </div>
                  <p className="text-xs opacity-80 mt-1">{t.reason}</p>
                  {t.evidence && (
                    <p className="text-[10px] opacity-60 mt-1 font-mono">{t.evidence}</p>
                  )}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-white/10 p-5">
            <h3 className="font-semibold mb-3">Affected APIs</h3>
            {result.affected_apis.length === 0 ? (
              <p className="text-sm text-gray-500">None in verified blast radius.</p>
            ) : (
              <ul className="space-y-2">
                {result.affected_apis.map((api) => (
                  <li key={api.node_id} className="text-sm p-2 rounded-lg bg-gray-900 border border-gray-800">
                    <span className="font-mono text-green-400">
                      {api.method} {api.path}
                    </span>
                    <p className="text-[10px] text-gray-600 mt-1">{api.inclusion_reason}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {activeTab === 'deploy' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-2xl border border-white/10 p-5 space-y-3">
            <div className="flex items-center gap-2">
              <Rocket className="w-5 h-5 text-cyan-400" />
              <h3 className="font-semibold">Rollout strategy</h3>
            </div>
            <p className="text-sm text-gray-400">{result.rollout_strategy.strategy}</p>
            <ul className="text-sm text-gray-300 space-y-1">
              {result.rollout_strategy.steps.map((s, i) => (
                <li key={i}>→ {s}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-white/10 p-5 space-y-3">
            <h3 className="font-semibold">Rollback & monitoring</h3>
            <p className="text-sm text-red-400/90">{result.rollback_strategy.trigger}</p>
            <ul className="text-sm text-gray-400 space-y-1">
              {result.rollback_strategy.steps.map((s, i) => (
                <li key={i}>{i + 1}. {s}</li>
              ))}
            </ul>
            <p className="text-xs text-gray-500 uppercase mt-4">Monitor</p>
            <ul className="text-sm text-gray-400">
              {result.monitoring_plan.map((m, i) => (
                <li key={i}>• {m}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3 space-y-2 max-h-[480px] overflow-y-auto">
            <h3 className="font-semibold sticky top-0 bg-[#09090b] py-2">
              Affected functions ({result.impacted_nodes.length})
            </h3>
            {result.impacted_nodes.map((node) => (
              <div
                key={node.id}
                className="p-3 rounded-xl border border-gray-800"
                style={{ marginLeft: node.depth * 8 }}
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium">{node.name}</span>
                  <NodeTypeBadge type={node.node_type} />
                </div>
                <p className="text-xs text-gray-500">{node.file_path}</p>
                {node.inclusion_reason && (
                  <p className="text-[10px] text-gray-600 mt-1 border-l-2 border-gray-700 pl-2">
                    {node.inclusion_reason}
                  </p>
                )}
              </div>
            ))}
          </div>
          <div className="lg:col-span-2">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Globe className="w-4 h-4" />
              Services & files
            </h3>
            <div className="flex flex-wrap gap-2 mb-4">
              {result.affected_systems.map((s) => (
                <span key={s} className="text-xs px-2 py-1 rounded-full bg-purple-950/50 border border-purple-800/40">
                  {s}
                </span>
              ))}
            </div>
            <ul className="space-y-2">
              {result.impacted_files.map((file) => (
                <li key={file.file_path}>
                  <Link
                    to={`/repos/${repoId}?file=${encodeURIComponent(file.file_path)}`}
                    className="block p-3 rounded-xl border border-gray-800 hover:border-gray-600"
                  >
                    <div className="flex justify-between">
                      <span className="text-sm truncate">{file.file_name}</span>
                      <RiskBadge level={file.risk_level} size="sm" />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  )
}
