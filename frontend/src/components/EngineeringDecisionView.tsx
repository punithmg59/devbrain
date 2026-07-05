import { useState } from 'react'
import { Copy, Share2, ArrowLeft, ChevronDown, ChevronUp, AlertTriangle, CheckCircle, XCircle, Clock, FileText, Database, Server, Code, Layers } from 'lucide-react'
import type { EngineeringReport } from '../types/engineeringReport'
import CallersDrawer from './CallersDrawer'
import SimulationUI from './simulation/SimulationUI'

interface Props {
  report: EngineeringReport
  timing?: Record<string, number>
  onCopyReport: () => void
  onShare: () => void
  onBack: () => void
}

function getVerdictFromReport(report: EngineeringReport): 'DO_NOT_DELETE' | 'HIGH_RISK' | 'PROCEED_WITH_CAUTION' | 'SAFE_TO_CHANGE' {
  const hero = report.hero as Record<string, unknown> | null
  const riskScore = hero?.risk_score as number ?? 50
  
  if (riskScore >= 80) return 'DO_NOT_DELETE'
  if (riskScore >= 60) return 'HIGH_RISK'
  if (riskScore >= 40) return 'PROCEED_WITH_CAUTION'
  return 'SAFE_TO_CHANGE'
}

function getTargetName(report: EngineeringReport): string {
  const hero = report.hero as Record<string, unknown> | null
  return (hero?.target_name as string) ?? report.title ?? 'Unknown Target'
}

export default function EngineeringDecisionView({
  report,
  timing,
  onCopyReport,
  onShare,
  onBack
}: Props) {
  const [callersDrawerOpen, setCallersDrawerOpen] = useState(false)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [showSimulation, setShowSimulation] = useState(false)

  const verdict = getVerdictFromReport(report)
  const targetName = getTargetName(report)
  
  const hero = report.hero as Record<string, unknown> | null
  const riskScore = hero?.risk_score as number ?? 50
  const confidence = hero?.confidence as number ?? 0.8
  const impactCount = hero?.impact_count as number ?? 0
  const analysisTime = timing?.total_ms ? (timing.total_ms / 1000).toFixed(2) : '0.00'
  const summary = hero?.executive_summary as string ?? report.title ?? 'No summary available'
  const reasoning = hero?.reasoning as string[] ?? []
  const nodeId = (hero?.node_id as string) ?? null
  const repoId = (hero?.repo_id as string) ?? 'demo-repo'
  const [showMoreActions, setShowMoreActions] = useState(false)
  const [showAnalysisDetails, setShowAnalysisDetails] = useState(false)

  const handleShowCallers = () => {
    if (nodeId) {
      setSelectedNodeId(nodeId)
      setCallersDrawerOpen(true)
    }
  }

  const handleNavigateToFile = (file: string, line?: number) => {
    // TODO: Integrate with Repository Explorer navigation
    console.log('Navigate to file:', file, 'line:', line)
    // This would typically navigate to the RepoDetailPage with the file selected
  }
  
  // Impact data
  const affectedAPIs = hero?.affected_apis as string[] ?? []
  const affectedServices = hero?.affected_services as string[] ?? []
  const affectedFiles = hero?.affected_files as string[] ?? []
  const affectedClasses = hero?.affected_classes as string[] ?? []
  const affectedTables = hero?.affected_tables as string[] ?? []
  const affectedWorkflows = hero?.affected_workflows as string[] ?? []
  
  // Recommendations as timeline
  const recommendations = hero?.recommendations as string[] ?? []
  const timelineSteps = recommendations.map((rec, i): { title: string; description: string; status: 'current' | 'pending' | 'completed' } => ({
    title: rec.split(':')[0] || `Step ${i + 1}`,
    description: rec.split(':').slice(1).join(':').trim() || rec,
    status: i === 0 ? 'current' : 'pending'
  }))
  
  // Evidence data
  const topCallers = hero?.top_callers as string[] ?? []
  const criticalDeps = hero?.critical_dependencies as string[] ?? []
  const graphRefs = hero?.graph_references as string[] ?? []
  const repoPaths = hero?.repository_paths as string[] ?? []
  const centrality = hero?.centrality as number ?? 0
  const riskFactors = hero?.risk_factors as string[] ?? []
  
  // Analysis details
  const intent = report.intent ?? 'Change impact analysis'
  const repoVersion = (hero?.repository_version as string) ?? 'latest'
  const timestamp = (report.generated_at as string) ?? new Date().toISOString()

  return (
    <div className="min-h-screen bg-[#09090b]">
      {/* Sticky Header */}
      <div className="sticky top-0 z-10 bg-[#09090b]/90 backdrop-blur-xl border-b border-gray-800">
        <div className="max-w-[90%] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
              aria-label="Go back"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="font-semibold text-white text-lg">Engineering Decision</h1>
              <p className="text-xs text-gray-500">{targetName}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onCopyReport}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
              aria-label="Copy report"
            >
              <Copy className="w-4 h-4" />
              Copy
            </button>
            <button
              onClick={onShare}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
              aria-label="Share report"
            >
              <Share2 className="w-4 h-4" />
              Share
            </button>
          </div>
        </div>
      </div>

      {/* Main Content - 90% width */}
      <div className="max-w-[90%] mx-auto px-6 py-8 space-y-6 animate-fade-in">
        {/* SECTION 1: Verdict Hero with WHY explanation */}
        <div className={`rounded-2xl border p-8 ${
          verdict === 'DO_NOT_DELETE'
            ? 'border-red-500/30 bg-red-950/20'
            : verdict === 'HIGH_RISK'
            ? 'border-orange-500/30 bg-orange-950/20'
            : verdict === 'PROCEED_WITH_CAUTION'
            ? 'border-yellow-500/30 bg-yellow-950/20'
            : 'border-green-500/30 bg-green-950/20'
        }`}>
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-4">
              {verdict === 'DO_NOT_DELETE' && <XCircle className="w-8 h-8 text-red-400" />}
              {verdict === 'HIGH_RISK' && <AlertTriangle className="w-8 h-8 text-orange-400" />}
              {verdict === 'PROCEED_WITH_CAUTION' && <AlertTriangle className="w-8 h-8 text-yellow-400" />}
              {verdict === 'SAFE_TO_CHANGE' && <CheckCircle className="w-8 h-8 text-green-400" />}
              <div>
                <h1 className="text-2xl font-bold text-white">
                  {verdict === 'DO_NOT_DELETE' && 'Do Not Delete'}
                  {verdict === 'HIGH_RISK' && 'High Risk'}
                  {verdict === 'PROCEED_WITH_CAUTION' && 'Proceed with Caution'}
                  {verdict === 'SAFE_TO_CHANGE' && 'Safe to Change'}
                </h1>
                <p className="text-gray-400 mt-1">{targetName}</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-white">{Math.round(confidence * 100)}%</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider">Confidence</div>
            </div>
          </div>
          
          {/* WHY explanation */}
          <div className="bg-black/20 rounded-lg p-4 mb-4">
            <p className="text-gray-300 text-sm leading-relaxed">{summary}</p>
          </div>

          {/* Quick metrics */}
          <div className="flex gap-6 text-sm">
            <div className="flex items-center gap-2 text-gray-400">
              <Clock className="w-4 h-4" />
              <span>{analysisTime}s analysis</span>
            </div>
            <div className="flex items-center gap-2 text-gray-400">
              <Server className="w-4 h-4" />
              <span>{impactCount} components affected</span>
            </div>
          </div>
        </div>

        {/* SECTION 2: Impact Summary - What breaks? */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/30 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">What Breaks</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Server className="w-4 h-4 text-blue-400" />
                <span className="text-xs text-gray-500 uppercase tracking-wider">APIs</span>
              </div>
              <div className="text-2xl font-bold text-white">{affectedAPIs.length}</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Server className="w-4 h-4 text-purple-400" />
                <span className="text-xs text-gray-500 uppercase tracking-wider">Services</span>
              </div>
              <div className="text-2xl font-bold text-white">{affectedServices.length}</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-green-400" />
                <span className="text-xs text-gray-500 uppercase tracking-wider">Files</span>
              </div>
              <div className="text-2xl font-bold text-white">{affectedFiles.length}</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Database className="w-4 h-4 text-orange-400" />
                <span className="text-xs text-gray-500 uppercase tracking-wider">Tables</span>
              </div>
              <div className="text-2xl font-bold text-white">{affectedTables.length}</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Code className="w-4 h-4 text-cyan-400" />
                <span className="text-xs text-gray-500 uppercase tracking-wider">Est. Effort</span>
              </div>
              <div className="text-2xl font-bold text-white">{impactCount > 10 ? 'High' : impactCount > 5 ? 'Medium' : 'Low'}</div>
            </div>
          </div>
        </div>

        {/* SECTION 3: Recommended Approach - What should I do instead? */}
        {timelineSteps.length > 0 && (
          <div className="rounded-2xl border border-gray-800 bg-gray-900/30 p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Recommended Approach</h2>
            <div className="space-y-3">
              {timelineSteps.slice(0, 5).map((step, index) => (
                <div key={index} className="flex items-start gap-4">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                    step.status === 'current' ? 'bg-purple-600 text-white' : 'bg-gray-700 text-gray-400'
                  }`}>
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-white">{step.title}</h3>
                    <p className="text-sm text-gray-400 mt-1">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SECTION 4: Primary Actions - What can I do next? */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/30 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Actions</h2>
          <div className="space-y-3">
            {/* Primary Action 1 */}
            <button
              onClick={handleShowCallers}
              className="w-full flex items-center justify-between p-4 bg-gray-800/50 hover:bg-gray-800 rounded-lg transition-colors group"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/10">
                  <Server className="w-5 h-5 text-purple-400" />
                </div>
                <div className="text-left">
                  <div className="font-medium text-white">View All Callers</div>
                  <div className="text-sm text-gray-500">See complete dependency graph</div>
                </div>
              </div>
              <ArrowLeft className="w-4 h-4 text-gray-500 group-hover:text-white rotate-180" />
            </button>

            {/* Primary Action 2 */}
            <button
              onClick={() => setShowSimulation(true)}
              className="w-full flex items-center justify-between p-4 bg-gray-800/50 hover:bg-gray-800 rounded-lg transition-colors group"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-cyan-500/10">
                  <AlertTriangle className="w-5 h-5 text-cyan-400" />
                </div>
                <div className="text-left">
                  <div className="font-medium text-white">Simulate Change</div>
                  <div className="text-sm text-gray-500">Predict cascade effects</div>
                </div>
              </div>
              <ArrowLeft className="w-4 h-4 text-gray-500 group-hover:text-white rotate-180" />
            </button>

            {/* Primary Action 3 */}
            <button className="w-full flex items-center justify-between p-4 bg-gray-800/50 hover:bg-gray-800 rounded-lg transition-colors group">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/10">
                  <FileText className="w-5 h-5 text-green-400" />
                </div>
                <div className="text-left">
                  <div className="font-medium text-white">Generate Migration Plan</div>
                  <div className="text-sm text-gray-500">Step-by-step refactoring guide</div>
                </div>
              </div>
              <ArrowLeft className="w-4 h-4 text-gray-500 group-hover:text-white rotate-180" />
            </button>

            {/* More Actions Expandable */}
            <button
              onClick={() => setShowMoreActions(!showMoreActions)}
              className="w-full flex items-center justify-between p-3 text-sm text-gray-500 hover:text-white transition-colors"
            >
              <span>{showMoreActions ? 'Show Less' : 'More Actions'}</span>
              {showMoreActions ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showMoreActions && (
              <div className="space-y-2 pt-2 border-t border-gray-800">
                <button className="w-full flex items-center gap-3 p-3 text-sm text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition-colors">
                  <Layers className="w-4 h-4" />
                  <span>Open Dependency Graph</span>
                </button>
                <button className="w-full flex items-center gap-3 p-3 text-sm text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition-colors">
                  <FileText className="w-4 h-4" />
                  <span>Export Report</span>
                </button>
                <button className="w-full flex items-center gap-3 p-3 text-sm text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition-colors">
                  <Share2 className="w-4 h-4" />
                  <span>Share with Team</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* SECTION 5: Change Simulation (conditional) */}
        {showSimulation && (
          <SimulationUI
            repoId={repoId}
            targetName={targetName}
            changeType="delete"
            targetType={hero?.target_type as string}
          />
        )}

        {/* SECTION 6: Collapsed Analysis Details */}
        <button
          onClick={() => setShowAnalysisDetails(!showAnalysisDetails)}
          className="w-full flex items-center justify-between p-4 rounded-xl border border-gray-800 bg-gray-900/30 hover:bg-gray-900/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <FileText className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-500">Analysis Details</span>
          </div>
          {showAnalysisDetails ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
        </button>

        {showAnalysisDetails && (
          <div className="rounded-xl border border-gray-800 bg-gray-900/30 p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-500 mb-1">Intent</div>
                <div className="text-white">{intent}</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">Execution Time</div>
                <div className="text-white">{analysisTime}s</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">Confidence</div>
                <div className="text-white">{Math.round(confidence * 100)}%</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">Repository Version</div>
                <div className="text-white">{repoVersion}</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">Analysis Timestamp</div>
                <div className="text-white">{new Date(timestamp).toLocaleString()}</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">Risk Score</div>
                <div className="text-white">{riskScore}/100</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Callers Drawer */}
      <CallersDrawer
        isOpen={callersDrawerOpen}
        onClose={() => setCallersDrawerOpen(false)}
        repoId={repoId}
        nodeId={selectedNodeId ?? ''}
        onNavigateToFile={handleNavigateToFile}
      />
    </div>
  )
}
