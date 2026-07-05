import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Loader2, AlertTriangle } from 'lucide-react'
import { ImpactSearchBar } from '../components/impact/ImpactSearchBar'
import { BlastRadiusGraphV3 } from '../components/impact/BlastRadiusGraphV3'
import { AffectedNodesList } from '../components/impact/AffectedNodesList'
import { RiskScoreDial } from '../components/impact/RiskScoreDial'
import { RecommendationsPanel } from '../components/impact/RecommendationsPanel'
import { impactService } from '../services/impactService'
import type { ImpactResultV3, NodeSearchResult, AffectedNode, ImpactHistoryItem } from '../types/impact'

export default function ImpactPageV3() {
  const { repoId } = useParams<{ repoId: string }>()
  const [result, setResult] = useState<ImpactResultV3 | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<ImpactHistoryItem[]>([])
  const [topNodes, setTopNodes] = useState<NodeSearchResult[]>([])

  useEffect(() => {
    if (!repoId) return

    const loadData = async () => {
      try {
        const [top, hist] = await Promise.all([
          impactService.getTopImpactNodes(repoId),
          impactService.getImpactHistory(repoId),
        ])
        setTopNodes(top)
        setHistory(hist)
      } catch (err) {
        console.error('Failed to load initial data:', err)
      }
    }

    loadData()
  }, [repoId])

  const handleAnalyze = useCallback(async (node: NodeSearchResult) => {
    if (!repoId) return

    setIsAnalyzing(true)
    setError(null)

    try {
      const res = await impactService.analyzeImpactV3(node.id, repoId)
      setResult(res)
      
      // Refresh history after new analysis
      const newHistory = await impactService.getImpactHistory(repoId)
      setHistory(newHistory)
    } catch (err) {
      setError('Analysis failed. Please try again.')
    } finally {
      setIsAnalyzing(false)
    }
  }, [repoId])

  const handleNodeClick = useCallback((node: AffectedNode) => {
    // Handle node click - could show details or trigger re-analysis
    console.log('Node clicked:', node)
  }, [])

  if (!repoId) {
    return (
      <div className="min-h-screen bg-[#0D1117] text-white flex items-center justify-center">
        <p className="text-gray-400">Repository ID not found</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0D1117] text-white flex flex-col">
      {/* Header */}
      <header className="border-b border-white/10 px-6 py-4">
        <div className="max-w-[1800px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to={`/repos/${repoId}`}
              className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold">What breaks?</h1>
              <p className="text-sm text-gray-400">Impact Analysis</p>
            </div>
          </div>
        </div>
      </header>

      {/* Search Bar */}
      <div className="border-b border-white/10 px-6 py-4">
        <div className="max-w-[1800px] mx-auto">
          <ImpactSearchBar
            repoId={repoId}
            onAnalyze={handleAnalyze}
            isAnalyzing={isAnalyzing}
          />
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="px-6 py-4">
          <div className="max-w-[1800px] mx-auto">
            <div className="flex items-center gap-2 p-4 rounded-lg bg-red-950/20 border border-red-500/30 text-red-400">
              <AlertTriangle className="w-5 h-5" />
              <span>{error}</span>
            </div>
          </div>
        </div>
      )}

      {/* Main Content - 3 Column Layout */}
      <div className="flex-1 px-6 py-6 overflow-hidden">
        <div className="max-w-[1800px] mx-auto h-full grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left Sidebar - 280px */}
          <aside className="lg:col-span-2 flex flex-col gap-6 overflow-y-auto">
            {result ? (
              <>
                <RiskScoreDial
                  score={result.risk_score}
                  blastRadius={result.blast_radius ?? 0}
                  effortLabel={result.effort_estimate?.label ?? 'Medium effort'}
                />
                <AffectedNodesList
                  affectedApis={result.affected_apis ?? []}
                  affectedServices={result.affected_services ?? []}
                  affectedTables={result.affected_tables ?? []}
                  affectedNodes={result.affected_nodes}
                  onNodeClick={handleNodeClick}
                />
              </>
            ) : (
              <div className="bg-[#161B22] border border-white/10 rounded-lg p-6">
                <h3 className="text-sm font-semibold text-white mb-4">Top Risk Components</h3>
                {topNodes.length === 0 ? (
                  <p className="text-xs text-gray-500">No components analyzed yet</p>
                ) : (
                  <div className="space-y-2">
                    {topNodes.slice(0, 5).map((node) => (
                      <button
                        key={node.id}
                        onClick={() => handleAnalyze(node)}
                        className="w-full text-left p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                      >
                        <div className="text-sm font-medium text-white truncate">{node.name}</div>
                        <div className="text-xs text-gray-500 mt-1">Blast radius: {node.blast_radius ?? 0}</div>
                      </button>
                    ))}
                  </div>
                )}
                <p className="text-xs text-gray-500 mt-4">Click any component to analyze its impact</p>
              </div>
            )}
          </aside>

          {/* Center Graph - Flex */}
          <main className="lg:col-span-7 h-[calc(100vh-280px)]">
            <div className="h-full bg-[#161B22] border border-white/10 rounded-lg overflow-hidden">
              {isAnalyzing ? (
                <div className="w-full h-full flex flex-col items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-purple-500 mb-4" />
                  <p className="text-sm text-gray-300">Traversing dependency graph...</p>
                  <p className="text-xs text-gray-500 mt-2">Calculating blast radius</p>
                </div>
              ) : (
                <BlastRadiusGraphV3
                  result={result}
                  onNodeClick={handleNodeClick}
                />
              )}
            </div>
          </main>

          {/* Right Panel - 300px */}
          <aside className="lg:col-span-3 flex flex-col gap-6 overflow-y-auto">
            <RecommendationsPanel
              recommendations={result?.recommendations || []}
              history={history}
              isLoading={isAnalyzing}
            />
          </aside>
        </div>
      </div>
    </div>
  )
}
