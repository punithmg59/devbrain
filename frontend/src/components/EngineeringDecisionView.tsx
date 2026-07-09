import { useState } from 'react'
import { Copy, Share2, ArrowLeft, X } from 'lucide-react'
import type { EngineeringReport } from '../types/engineeringReport'
import QuestionBar from './engineering-decision/QuestionBar'
import EngineeringDecisionHero from './engineering-decision/EngineeringDecisionHero'
import ImpactSummary from './engineering-decision/ImpactSummary'
import WhySection from './engineering-decision/WhySection'
import RecommendedApproach from './engineering-decision/RecommendedApproach'
import EngineeringActions from './engineering-decision/EngineeringActions'
import SupportingEvidence from './engineering-decision/SupportingEvidence'
import AnalysisDetails from './engineering-decision/AnalysisDetails'
import CallersDrawer from './CallersDrawer'
import SimulationUI from './simulation/SimulationUI'
import MigrationPlanDrawer from './MigrationPlanDrawer'
import TestingChecklistDrawer from './TestingChecklistDrawer'
import ImpactDependencyGraph from './ImpactDependencyGraph'

interface Props {
  report: EngineeringReport
  timing?: Record<string, number>
  onCopyReport: () => void
  onShare: () => void
  onBack: () => void
}

function getVerdictFromReport(report: EngineeringReport): 'SAFE' | 'MODERATE' | 'HIGH_RISK' | 'CRITICAL' {
  const hero = report.hero as Record<string, unknown> | null
  const riskScore = hero?.risk_score as number ?? 50
  
  if (riskScore >= 80) return 'CRITICAL'
  if (riskScore >= 60) return 'HIGH_RISK'
  if (riskScore >= 40) return 'MODERATE'
  return 'SAFE'
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
  const [hasAnalyzed, setHasAnalyzed] = useState(false)
  const [migrationPlanOpen, setMigrationPlanOpen] = useState(false)
  const [testingChecklistOpen, setTestingChecklistOpen] = useState(false)
  const [dependencyGraphOpen, setDependencyGraphOpen] = useState(false)

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

  const handleShowCallers = () => {
    if (nodeId) {
      setSelectedNodeId(nodeId)
      setCallersDrawerOpen(true)
    }
  }

  const handleNavigateToFile = (file: string, line?: number) => {
    console.log('Navigate to file:', file, 'line:', line)
  }

  const handleAnalyze = (query: string) => {
    setHasAnalyzed(true)
    // Trigger analysis with the query
    console.log('Analyzing:', query)
  }

  // Impact data
  const affectedAPIs = hero?.affected_apis as string[] ?? []
  const affectedServices = hero?.affected_services as string[] ?? []
  const affectedFiles = hero?.affected_files as string[] ?? []
  const affectedClasses = hero?.affected_classes as string[] ?? []
  const affectedTables = hero?.affected_tables as string[] ?? []
  const affectedWorkflows = hero?.affected_workflows as string[] ?? []
  
  // Calculate deployment risk based on impact
  const getDeploymentRisk = (): 'Low' | 'Medium' | 'High' => {
    if (impactCount > 20) return 'High'
    if (impactCount > 10) return 'Medium'
    return 'Low'
  }

  // Calculate estimated test failures
  const estimatedTestFailures = Math.floor(impactCount * 0.6)
  
  // Calculate engineering effort
  const getEngineeringEffort = (): string => {
    if (impactCount > 20) return '2-3 days'
    if (impactCount > 10) return '1-2 days'
    if (impactCount > 5) return '4-8 hours'
    return '1-3 hours'
  }

  // Recommendations as timeline
  const recommendations = hero?.recommendations as string[] ?? []
  const timelineSteps = recommendations.slice(0, 5).map((rec, i) => ({
    title: rec.split(':')[0] || `Step ${i + 1}`,
    description: rec.split(':').slice(1).join(':').trim() || rec,
    timeEstimate: i === 0 ? '1 hour' : i === 1 ? '4 hours' : i === 2 ? '2 hours' : '30 minutes',
    status: (i === 0 ? 'current' : 'pending') as 'current' | 'pending' | 'completed'
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
        {!hasAnalyzed ? (
          /* Question Bar */
          <QuestionBar onAnalyze={handleAnalyze} />
        ) : (
          <>
            {/* SECTION 1: Engineering Decision Hero */}
            <EngineeringDecisionHero
              verdict={verdict}
              targetName={targetName}
              riskScore={riskScore}
              confidence={confidence}
              blastRadius={impactCount}
              engineeringEffort={getEngineeringEffort()}
              whySentence={summary}
            />

            {/* SECTION 2: Impact Summary */}
            <ImpactSummary
              affectedAPIs={affectedAPIs.length}
              affectedServices={affectedServices.length}
              affectedFiles={affectedFiles.length}
              affectedClasses={affectedClasses.length}
              affectedTables={affectedTables.length}
              affectedWorkflows={affectedWorkflows.length}
              estimatedTestFailures={estimatedTestFailures}
              deploymentRisk={getDeploymentRisk()}
            />

            {/* SECTION 3: Why Section */}
            <WhySection reasons={reasoning} />

            {/* SECTION 4: Recommended Approach */}
            {timelineSteps.length > 0 && (
              <RecommendedApproach
                steps={timelineSteps}
                onGenerateChecklist={() => console.log('Generate checklist')}
                onExportPlan={() => console.log('Export plan')}
              />
            )}

            {/* SECTION 5: Engineering Actions */}
            <EngineeringActions
              onShowCallers={handleShowCallers}
              onShowSimulation={() => setShowSimulation(true)}
              onOpenDependencyGraph={() => setDependencyGraphOpen(true)}
              onGenerateMigrationPlan={() => setMigrationPlanOpen(true)}
              onGenerateTestingChecklist={() => setTestingChecklistOpen(true)}
              onExportReport={onCopyReport}
              onShareWithTeam={onShare}
            />

            {/* SECTION 6: Change Simulation (conditional) */}
            {showSimulation && (
              <SimulationUI
                repoId={repoId}
                targetName={targetName}
                changeType="delete"
                targetType={hero?.target_type as string}
              />
            )}

            {/* SECTION 7: Supporting Evidence (collapsed) */}
            <SupportingEvidence
              topCallers={topCallers}
              criticalDependencies={criticalDeps}
              graphReferences={graphRefs}
              repositoryPaths={repoPaths}
              centrality={centrality}
              riskFactors={riskFactors}
            />

            {/* SECTION 8: Analysis Details (collapsed) */}
            <AnalysisDetails
              executionTime={analysisTime}
              pipelineTimings={timing ?? {}}
              intent={intent}
              confidence={confidence}
              repositoryVersion={repoVersion}
              analysisTimestamp={timestamp}
            />
          </>
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

      {/* Migration Plan Drawer */}
      <MigrationPlanDrawer
        isOpen={migrationPlanOpen}
        onClose={() => setMigrationPlanOpen(false)}
        repoId={repoId}
        targetName={targetName}
        targetType={hero?.target_type as string}
        changeType="delete"
      />

      {/* Testing Checklist Drawer */}
      <TestingChecklistDrawer
        isOpen={testingChecklistOpen}
        onClose={() => setTestingChecklistOpen(false)}
        repoId={repoId}
        targetName={targetName}
        targetType={hero?.target_type as string}
      />

      {/* Dependency Graph Modal */}
      {dependencyGraphOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-[#09090b] border border-gray-800 rounded-2xl w-[90%] max-w-5xl max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
              <div>
                <h2 className="text-xl font-semibold text-white">Dependency Graph</h2>
                <p className="text-sm text-gray-500 mt-1">{targetName}</p>
              </div>
              <button
                onClick={() => setDependencyGraphOpen(false)}
                className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6">
              <ImpactDependencyGraph graph={null} className="w-full" />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
