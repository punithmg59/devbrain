import { useState } from 'react'
import { 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  ChevronDown, 
  ChevronUp,
  Copy,
  Share2,
  ArrowRight,
  FileCode,
  Globe,
  Database,
  Building2,
  GitBranch,
  TestTube,
  Network,
  Zap,
  Clock,
  Target,
  Shield,
  TrendingUp,
  Layers,
  Code2,
  Search,
  FileText,
  BarChart3,
  Play,
  Download,
  ExternalLink,
  Brain
} from 'lucide-react'
import type { ImpactResult } from '../types/impact'

interface Props {
  result: ImpactResult
  onCopyReport: () => void
  onShare: () => void
}

function getVerdictIcon(riskScore: number) {
  if (riskScore >= 80) return <XCircle className="w-8 h-8" />
  if (riskScore >= 60) return <AlertTriangle className="w-8 h-8" />
  return <CheckCircle className="w-8 h-8" />
}

function getVerdictLabel(riskScore: number) {
  if (riskScore >= 80) return 'DO NOT DELETE'
  if (riskScore >= 60) return 'HIGH RISK'
  if (riskScore >= 40) return 'PROCEED WITH CAUTION'
  return 'SAFE TO CHANGE'
}

function getVerdictColor(riskScore: number) {
  if (riskScore >= 80) return 'text-red-400 border-red-500/30 bg-red-950/20'
  if (riskScore >= 60) return 'text-orange-400 border-orange-500/30 bg-orange-950/20'
  if (riskScore >= 40) return 'text-yellow-400 border-yellow-500/30 bg-yellow-950/20'
  return 'text-green-400 border-green-500/30 bg-green-950/20'
}

function CollapsibleSection({ 
  title, 
  icon, 
  children, 
  defaultOpen = false 
}: { 
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  
  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900/30 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-800/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          {icon}
          <span className="font-semibold text-gray-200">{title}</span>
        </div>
        {isOpen ? <ChevronUp className="w-5 h-5 text-gray-500" /> : <ChevronDown className="w-5 h-5 text-gray-500" />}
      </button>
      {isOpen && <div className="px-6 pb-6">{children}</div>}
    </div>
  )
}

function ImpactCard({ 
  title, 
  icon, 
  count, 
  items, 
  color 
}: { 
  title: string
  icon: React.ReactNode
  count: number
  items: string[]
  color: string
}) {
  if (count === 0) return null
  
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
      <div className={`flex items-center gap-2 mb-3 ${color}`}>
        {icon}
        <span className="text-sm font-semibold">{title}</span>
        <span className="ml-auto text-xs text-gray-500">{count}</span>
      </div>
      <div className="space-y-1.5 max-h-40 overflow-y-auto">
        {items.slice(0, 5).map((item, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <ArrowRight className="w-3 h-3 mt-0.5 text-gray-600 shrink-0" />
            <span className="text-gray-300 truncate">{item}</span>
          </div>
        ))}
        {items.length > 5 && (
          <div className="text-xs text-gray-500 mt-2">
            +{items.length - 5} more
          </div>
        )}
      </div>
    </div>
  )
}

function ActionCard({ 
  icon, 
  title, 
  description 
}: { 
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <button className="w-full text-left p-5 rounded-xl border border-gray-800 bg-gray-900/40 hover:border-purple-500/50 hover:bg-purple-950/10 transition-all group">
      <div className="flex items-start gap-4">
        <div className="p-2 rounded-lg bg-gray-800 group-hover:bg-purple-900/30 transition-colors">
          {icon}
        </div>
        <div className="flex-1">
          <h4 className="font-semibold text-gray-200 mb-1">{title}</h4>
          <p className="text-xs text-gray-500">{description}</p>
        </div>
        <ArrowRight className="w-4 h-4 text-gray-600 group-hover:text-purple-400 transition-colors mt-1" />
      </div>
    </button>
  )
}

export default function EngineeringReportView({
  result,
  onCopyReport,
  onShare,
}: Props) {
  const riskScore = result.risk_score_100 ?? 0
  const verdictColor = getVerdictColor(riskScore)
  const verdictIcon = getVerdictIcon(riskScore)
  const verdictLabel = getVerdictLabel(riskScore)
  
  const analysisTime = (result.analysis_time_ms / 1000).toFixed(2)
  
  return (
    <div className="min-h-screen bg-[#09090b]">
      {/* Header Actions */}
      <div className="sticky top-0 z-10 bg-[#09090b]/80 backdrop-blur-xl border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-purple-600/20 flex items-center justify-center">
              <Shield className="w-4 h-4 text-purple-400" />
            </div>
            <span className="font-semibold text-gray-200">Engineering Report</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onCopyReport}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            >
              <Copy className="w-4 h-4" />
              Copy
            </button>
            <button
              onClick={onShare}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            >
              <Share2 className="w-4 h-4" />
              Share
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* SECTION 1: Engineering Verdict */}
        <div className={`rounded-2xl border p-8 ${verdictColor}`}>
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-xl bg-gray-900/50 ${verdictColor.split(' ')[0]}`}>
                {verdictIcon}
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white mb-1">{verdictLabel}</h1>
                <p className="text-sm text-gray-400">Risk Assessment</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-5xl font-bold text-white tabular-nums">{riskScore}</div>
              <div className="text-sm text-gray-400">/100 Risk Score</div>
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-8 pt-6 border-t border-gray-700/50">
            <div>
              <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                <Target className="w-4 h-4" />
                Confidence
              </div>
              <div className="text-2xl font-semibold text-white tabular-nums">
                {Math.round(result.confidence * 100)}%
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                <TrendingUp className="w-4 h-4" />
                Impact
              </div>
              <div className="text-2xl font-semibold text-white">
                {result.total_affected_functions} functions
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                <Clock className="w-4 h-4" />
                Analysis Time
              </div>
              <div className="text-2xl font-semibold text-white tabular-nums">
                {analysisTime}s
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                <Layers className="w-4 h-4" />
                Blast Radius
              </div>
              <div className="text-2xl font-semibold text-white">
                {result.blast_radius.total_nodes} nodes
              </div>
            </div>
          </div>
        </div>

        {/* SECTION 2: Executive Summary */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/30 p-8">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-semibold text-white">Executive Summary</h2>
          </div>
          <p className="text-gray-300 leading-relaxed text-lg">
            {result.executive_summary}
          </p>
        </div>

        {/* SECTION 3: Why DevBrain Reached This Decision */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/30 p-8">
          <div className="flex items-center gap-3 mb-4">
            <Brain className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-semibold text-white">Why DevBrain Reached This Decision</h2>
          </div>
          <ul className="space-y-3">
            {result.why_this_matters.split('.').filter(Boolean).map((reason, i) => (
              <li key={i} className="flex items-start gap-3 text-gray-300">
                <div className="w-1.5 h-1.5 rounded-full bg-purple-400 mt-2 shrink-0" />
                <span>{reason.trim()}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* SECTION 4: Impact Analysis */}
        <div className="space-y-4">
          <div className="flex items-center gap-3 mb-2">
            <BarChart3 className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-semibold text-white">Impact Analysis</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <ImpactCard
              title="Affected APIs"
              icon={<Globe className="w-4 h-4 text-green-400" />}
              count={result.affected_apis.length}
              items={result.affected_apis.map(api => `${api.method} ${api.path}`)}
              color="text-green-400"
            />
            <ImpactCard
              title="Affected Services"
              icon={<Building2 className="w-4 h-4 text-blue-400" />}
              count={result.affected_systems.length}
              items={result.affected_systems}
              color="text-blue-400"
            />
            <ImpactCard
              title="Affected Files"
              icon={<FileCode className="w-4 h-4 text-yellow-400" />}
              count={result.impacted_files.length}
              items={result.impacted_files.map(f => f.file_name)}
              color="text-yellow-400"
            />
            <ImpactCard
              title="Affected Classes"
              icon={<Code2 className="w-4 h-4 text-purple-400" />}
              count={result.blast_radius.classes}
              items={result.impacted_nodes.filter(n => n.node_type === 'class').map(n => n.name)}
              color="text-purple-400"
            />
            <ImpactCard
              title="Database Tables"
              icon={<Database className="w-4 h-4 text-red-400" />}
              count={result.exact_dependencies?.database_dependencies.length ?? 0}
              items={result.exact_dependencies?.database_dependencies.map(d => d.name) ?? []}
              color="text-red-400"
            />
            <ImpactCard
              title="Workflows"
              icon={<GitBranch className="w-4 h-4 text-cyan-400" />}
              count={result.workflow_impact.length}
              items={result.workflow_impact.map(w => w.workflow_name)}
              color="text-cyan-400"
            />
          </div>
        </div>

        {/* SECTION 5: Engineering Evidence */}
        <CollapsibleSection 
          title="Engineering Evidence" 
          icon={<Search className="w-5 h-5 text-gray-400" />}
          defaultOpen={false}
        >
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-semibold text-gray-300 mb-3">Top Callers</h4>
              <div className="space-y-2">
                {result.exact_dependencies?.level_1_incoming.slice(0, 5).map((dep, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50">
                    <div className="flex items-center gap-3">
                      <ArrowRight className="w-4 h-4 text-gray-500 rotate-180" />
                      <div>
                        <div className="text-sm font-medium text-gray-200">{dep.name}</div>
                        <div className="text-xs text-gray-500">{dep.file_path}</div>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500">{Math.round(dep.confidence * 100)}%</div>
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <h4 className="text-sm font-semibold text-gray-300 mb-3">Critical Dependencies</h4>
              <div className="space-y-2">
                {result.exact_dependencies?.level_1_direct.slice(0, 5).map((dep, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50">
                    <div className="flex items-center gap-3">
                      <ArrowRight className="w-4 h-4 text-gray-500" />
                      <div>
                        <div className="text-sm font-medium text-gray-200">{dep.name}</div>
                        <div className="text-xs text-gray-500">{dep.file_path}</div>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500">{Math.round(dep.confidence * 100)}%</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CollapsibleSection>

        {/* SECTION 6: Recommended Approach */}
        <div className="rounded-2xl border border-purple-500/20 bg-purple-950/10 p-8">
          <div className="flex items-center gap-3 mb-4">
            <Zap className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-semibold text-white">Recommended Approach</h2>
          </div>
          <div className="space-y-3">
            {result.staff_engineer_recommendation.split('.').filter(Boolean).map((step, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="flex items-center justify-center w-6 h-6 rounded-full bg-purple-600/20 text-purple-400 text-xs font-semibold shrink-0">
                  {i + 1}
                </div>
                <p className="text-gray-300">{step.trim()}</p>
              </div>
            ))}
          </div>
        </div>

        {/* SECTION 7: Engineering Actions */}
        <div className="space-y-4">
          <div className="flex items-center gap-3 mb-2">
            <Play className="w-5 h-5 text-green-400" />
            <h2 className="text-lg font-semibold text-white">Engineering Actions</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ActionCard
              icon={<Network className="w-5 h-5 text-purple-400" />}
              title="Show All Callers"
              description="View complete dependency graph of all calling functions"
            />
            <ActionCard
              icon={<Layers className="w-5 h-5 text-blue-400" />}
              title="Open Dependency Graph"
              description="Interactive visualization of the entire dependency tree"
            />
            <ActionCard
              icon={<FileText className="w-5 h-5 text-green-400" />}
              title="Generate Migration Plan"
              description="Step-by-step guide for safe refactoring"
            />
            <ActionCard
              icon={<TestTube className="w-5 h-5 text-yellow-400" />}
              title="Generate Testing Checklist"
              description="Comprehensive test coverage recommendations"
            />
            <ActionCard
              icon={<BarChart3 className="w-5 h-5 text-cyan-400" />}
              title="Estimate Refactoring Effort"
              description="Time and complexity estimates for the change"
            />
            <ActionCard
              icon={<Search className="w-5 h-5 text-orange-400" />}
              title="Locate Critical Files"
              description="Find high-risk files requiring special attention"
            />
            <ActionCard
              icon={<Download className="w-5 h-5 text-gray-400" />}
              title="Export Report"
              description="Download this analysis as a PDF document"
            />
            <ActionCard
              icon={<ExternalLink className="w-5 h-5 text-purple-400" />}
              title="Open in GitHub"
              description="View affected files directly in your repository"
            />
          </div>
        </div>

        {/* SECTION 8: Developer Details */}
        <CollapsibleSection 
          title="Developer Details" 
          icon={<Code2 className="w-5 h-5 text-gray-400" />}
          defaultOpen={false}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Intent</div>
                <div className="text-sm text-gray-300">{result.query}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Execution Time</div>
                <div className="text-sm text-gray-300">{analysisTime}s</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Scenario</div>
                <div className="text-sm text-gray-300 capitalize">{result.scenario}</div>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Repository Version</div>
                <div className="text-sm text-gray-300">{result.version ?? 'latest'}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Analysis Timestamp</div>
                <div className="text-sm text-gray-300">{new Date().toISOString()}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Confidence Score</div>
                <div className="text-sm text-gray-300">{Math.round(result.confidence * 100)}%</div>
              </div>
            </div>
          </div>
          
          <div className="mt-6 pt-6 border-t border-gray-800">
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">Pipeline Timings</div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-[10px] text-gray-600">Intent Resolution</div>
                <div className="text-sm text-gray-400">--</div>
              </div>
              <div>
                <div className="text-[10px] text-gray-600">Evidence Collection</div>
                <div className="text-sm text-gray-400">--</div>
              </div>
              <div>
                <div className="text-[10px] text-gray-600">Reasoning</div>
                <div className="text-sm text-gray-400">--</div>
              </div>
              <div>
                <div className="text-[10px] text-gray-600">Report Generation</div>
                <div className="text-sm text-gray-400">--</div>
              </div>
            </div>
          </div>
        </CollapsibleSection>
      </div>
    </div>
  )
}
