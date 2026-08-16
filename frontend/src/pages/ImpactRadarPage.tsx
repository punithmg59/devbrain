import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import axios from 'axios'
import { ArrowLeft, Loader2, Sparkles, Zap, Search, ChevronRight, AlertTriangle, Play, HelpCircle, Code, Server, Database, Key, LayoutGrid, Layers } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import NodeTypeBadge from '../components/NodeTypeBadge'
import { useToast } from '../components/Toast'
import { impactService } from '../services/impactService'
import { getRepoDetail } from '../services/repoDetailService'
import type { ImpactReportV2, AffectedItemV2 } from '../types/impact'
import type { AutocompleteSuggestion } from '../types/resolver'
import BlastRadiusGraph from '../components/BlastRadiusGraph'
import ImpactDependencyTree from '../components/ImpactDependencyTree'

const RECENT_KEY = 'devbrain-impact-recent-v2'
const LOADING_MESSAGES = [
  'Tracing upstream dependencies...',
  'Walking the import graph (depth ≤ 5)...',
  'Resolving database schema usage...',
  'Running scenario-specific risk engine...',
  'Analyzing security and auth dependencies...',
  'Formatting architectural explanation...',
]

function loadRecent(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY)
    return raw ? (JSON.parse(raw) as string[]) : []
  } catch {
    return []
  }
}

function saveRecent(query: string) {
  const prev = loadRecent().filter((q) => q !== query)
  localStorage.setItem(RECENT_KEY, JSON.stringify([query, ...prev].slice(0, 5)))
}

export default function ImpactRadarPage() {
  const { repoId } = useParams<{ repoId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { addToast } = useToast()

  const [searchQuery, setSearchQuery] = useState('')
  const [scenario, setScenario] = useState<'delete' | 'modify' | 'rename' | 'move'>('delete')
  const [newName, setNewName] = useState('')
  const [newFilePath, setNewFilePath] = useState('')
  
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState(LOADING_MESSAGES[0])
  const [result, setResult] = useState<ImpactReportV2 | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  const [autocompleteItems, setAutocompleteItems] = useState<AutocompleteSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [recent, setRecent] = useState<string[]>(loadRecent)
  const [activeTab, setActiveTab] = useState<'graph' | 'affected' | 'llm'>('graph')

  const debounceRef = useRef<ReturnType<typeof setTimeout>>()
  const analyzeAbortRef = useRef<AbortController | null>(null)

  const { data: repo } = useQuery({
    queryKey: ['repo-detail', repoId],
    queryFn: () => getRepoDetail(repoId!),
    enabled: !!repoId,
    staleTime: 5 * 60 * 1000,
  })

  const runAnalysis = useCallback(
    async (queryText: string) => {
      if (!repoId) return
      const q = queryText.trim()
      if (!q) {
        addToast('Please enter a node name or search query', 'error')
        return
      }

      analyzeAbortRef.current?.abort()
      const controller = new AbortController()
      analyzeAbortRef.current = controller

      setLoading(true)
      setError(null)
      saveRecent(q)
      setRecent(loadRecent())

      // Sync to URL parameters
      const params = new URLSearchParams(location.search)
      params.set('q', q)
      params.set('scenario', scenario)
      navigate(
        { pathname: location.pathname, search: params.toString() },
        { replace: true }
      )

      try {
        const data = await impactService.analyzeImpactV2(
          repoId,
          {
            query: q,
            scenario,
            new_name: scenario === 'rename' ? newName || undefined : undefined,
            new_file_path: scenario === 'move' ? newFilePath || undefined : undefined,
          },
          { signal: controller.signal }
        )
        if (controller.signal.aborted) return
        setResult(data)
        addToast('Graph impact analysis complete!', 'success')
      } catch (err: any) {
        if (axios.isCancel(err)) return
        const errMsg = err.response?.data?.detail || 'Analysis failed. Please try again.'
        setError(errMsg)
        addToast(errMsg, 'error')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    },
    [repoId, scenario, newName, newFilePath, navigate, location.pathname, location.search, addToast]
  )

  useEffect(() => {
    return () => {
      analyzeAbortRef.current?.abort()
    }
  }, [])

  // Loading spinner message rotation
  useEffect(() => {
    if (!loading) return
    let i = 0
    setLoadingMsg(LOADING_MESSAGES[0])
    const id = setInterval(() => {
      i = (i + 1) % LOADING_MESSAGES.length
      setLoadingMsg(LOADING_MESSAGES[i])
    }, 1200)
    return () => clearInterval(id)
  }, [loading])

  // Handle URL loading on mount
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const q = params.get('q')
    const scen = params.get('scenario')
    if (scen && ['delete', 'modify', 'rename', 'move'].includes(scen)) {
      setScenario(scen as any)
    }
    if (q && repoId) {
      setSearchQuery(q)
      runAnalysis(q)
    }
  }, [location.search, repoId])

  // Autocomplete fetcher
  useEffect(() => {
    if (!repoId || searchQuery.length < 2) {
      setAutocompleteItems([])
      return
    }
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        const data = await impactService.autocomplete(repoId, searchQuery)
        setAutocompleteItems(data.suggestions.slice(0, 10))
      } catch {
        setAutocompleteItems([])
      }
    }, 200)
    return () => clearTimeout(debounceRef.current)
  }, [searchQuery, repoId])

  const getRiskLevelColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'safe': return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10'
      case 'low': return 'text-green-400 border-green-500/20 bg-green-500/10'
      case 'medium': return 'text-amber-400 border-amber-500/20 bg-amber-500/10'
      case 'high': return 'text-orange-400 border-orange-500/20 bg-orange-500/10'
      case 'critical': return 'text-rose-400 border-rose-500/20 bg-rose-500/10'
      default: return 'text-gray-400 border-white/10 bg-white/5'
    }
  }

  const getRiskGaugeColor = (score: number) => {
    if (score <= 20) return 'bg-emerald-500'
    if (score <= 40) return 'bg-green-500'
    if (score <= 60) return 'bg-amber-500'
    if (score <= 80) return 'bg-orange-500'
    return 'bg-rose-500'
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-white flex flex-col font-sans selection:bg-purple-500/30">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-[#09090b]/80 backdrop-blur-xl shrink-0">
        <div className="max-w-[1600px] mx-auto flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <Link
              to={`/repos/${repoId}`}
              className="p-2 rounded-xl hover:bg-white/5 text-gray-400 hover:text-white transition-all"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div>
              <h1 className="font-semibold text-sm flex items-center gap-2">
                <Zap className="w-4 h-4 text-purple-400 animate-pulse" />
                Impact Radar
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono">
                  V2
                </span>
              </h1>
              {repo?.full_name && (
                <p className="text-xs text-gray-500">{repo.full_name}</p>
              )}
            </div>
          </div>
          <div className="text-xs text-gray-500 font-mono">
            Code Change Impact Analysis
          </div>
        </div>
      </header>

      {/* Main Content Workspace */}
      <div className="flex-1 max-w-[1600px] w-full mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-hidden">
        
        {/* COLUMN 1: Search & Configuration (col-span-3) */}
        <aside className="lg:col-span-3 flex flex-col gap-6">
          <div className="bg-[#18181b]/30 backdrop-blur-md border border-white/5 rounded-2xl p-5 shadow-xl flex flex-col gap-5">
            <div>
              <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                <Search className="w-4 h-4 text-purple-400" />
                Analyze a Code Change
              </h2>
              <p className="text-xs text-gray-500 mt-1">Select a function, class, or API route and see what could be affected by changing it.</p>
            </div>

            {/* Target search field */}
            <div className="relative">
              <label className="text-[10px] uppercase tracking-wider text-gray-500 font-bold block mb-1.5">
                Function / Class / API Route
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    setShowSuggestions(true)
                  }}
                  onFocus={() => setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                  placeholder="e.g. _batch_summarize"
                  className="w-full bg-white/5 border border-white/10 rounded-xl py-2.5 pl-3.5 pr-10 text-sm focus:outline-none focus:ring-1 focus:ring-purple-500/50 focus:border-purple-500/50 text-white placeholder-gray-600 transition-all"
                />
                <button
                  onClick={() => runAnalysis(searchQuery)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-all"
                >
                  <Play className="w-3.5 h-3.5" />
                </button>
              </div>

              {showSuggestions && autocompleteItems.length > 0 && (
                <ul className="absolute z-50 w-full mt-1.5 bg-[#121214] border border-white/10 rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto">
                  {autocompleteItems.map((s, idx) => (
                    <li key={`${s.label}-${idx}`}>
                      <button
                        type="button"
                        onClick={() => {
                          setSearchQuery(s.label)
                          setShowSuggestions(false)
                          runAnalysis(s.label)
                        }}
                        className="w-full px-3.5 py-2.5 text-left hover:bg-white/5 transition-colors flex flex-col gap-0.5 border-b border-white/[0.02] last:border-0"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-white truncate max-w-[180px]">{s.label}</span>
                          <NodeTypeBadge type={s.entity_type} />
                        </div>
                        {s.file_path && (
                          <span className="text-[10px] text-gray-500 truncate max-w-[220px]">
                            {s.file_path}
                          </span>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Scenario Picker */}
            <div>
              <label className="text-[10px] uppercase tracking-wider text-gray-500 font-bold block mb-1.5">
                Change Type
              </label>
              <div className="grid grid-cols-2 gap-2">
                {(['delete', 'modify', 'rename', 'move'] as const).map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setScenario(s)}
                    className={`py-2 rounded-xl text-xs font-medium border transition-all capitalize ${
                      scenario === s
                        ? 'bg-purple-500/10 border-purple-500 text-purple-300 font-semibold shadow-inner'
                        : 'border-white/5 hover:border-white/10 text-gray-400 hover:text-white'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* Dynamic Inputs depending on scenario */}
            {scenario === 'rename' && (
              <div className="animate-fadeIn">
                <label className="text-[10px] uppercase tracking-wider text-gray-500 font-bold block mb-1.5">
                  New Node Name
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. batch_summarize_nodes"
                  className="w-full bg-white/5 border border-white/10 rounded-xl py-2.5 px-3.5 text-sm focus:outline-none focus:ring-1 focus:ring-purple-500/50 text-white transition-all"
                />
              </div>
            )}

            {scenario === 'move' && (
              <div className="animate-fadeIn">
                <label className="text-[10px] uppercase tracking-wider text-gray-500 font-bold block mb-1.5">
                  New File Path
                </label>
                <input
                  type="text"
                  value={newFilePath}
                  onChange={(e) => setNewFilePath(e.target.value)}
                  placeholder="e.g. backend/app/utils/summarize.py"
                  className="w-full bg-white/5 border border-white/10 rounded-xl py-2.5 px-3.5 text-sm focus:outline-none focus:ring-1 focus:ring-purple-500/50 text-white transition-all"
                />
              </div>
            )}

            <button
              onClick={() => runAnalysis(searchQuery)}
              disabled={loading || !searchQuery.trim()}
              className="w-full h-11 bg-white hover:bg-gray-100 disabled:bg-white/10 disabled:text-gray-500 text-black font-semibold rounded-xl text-xs transition-all flex items-center justify-center gap-2 mt-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing Dependencies...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 fill-black" />
                  Analyze Impact
                </>
              )}
            </button>
          </div>

          {/* Recent Queries list */}
          {recent.length > 0 && !loading && (
            <div className="bg-[#18181b]/20 border border-white/5 rounded-2xl p-4 shadow-lg flex flex-col gap-2">
              <span className="text-[10px] uppercase tracking-wider text-gray-600 font-bold">Recent Searches</span>
              <div className="flex flex-col gap-1.5">
                {recent.map((q, idx) => (
                  <button
                    key={`${q}-${idx}`}
                    onClick={() => {
                      setSearchQuery(q)
                      runAnalysis(q)
                    }}
                    className="text-xs text-left text-gray-400 hover:text-white py-1 px-2 rounded hover:bg-white/[0.02] truncate transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
        </aside>

        {/* COLUMN 2: Analysis Results & LLM Exposer (col-span-6) */}
        <main className="lg:col-span-6 flex flex-col gap-6 overflow-y-auto pr-2 scrollbar-thin">
          
          {/* Loading state */}
          {loading && (
            <div className="flex-1 flex flex-col items-center justify-center p-12 bg-[#18181b]/10 border border-white/5 rounded-2xl min-h-[450px]">
              <div className="relative w-16 h-16 mb-6">
                <div className="absolute inset-0 rounded-full border-2 border-purple-500/20"></div>
                <div className="absolute inset-0 rounded-full border-2 border-t-purple-500 animate-spin"></div>
                <Zap className="w-6 h-6 text-purple-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
              </div>
              <p className="text-sm text-gray-300 font-medium">{loadingMsg}</p>
              <p className="text-xs text-gray-500 mt-2">Traversing graph paths and fetching database relations</p>
            </div>
          )}

          {/* Error state */}
          {error && !loading && (
            <div className="flex flex-col items-center justify-center p-8 bg-rose-500/5 border border-rose-500/20 rounded-2xl min-h-[300px]">
              <AlertTriangle className="w-10 h-10 text-rose-400 mb-3" />
              <h3 className="font-semibold text-rose-400 text-sm">Analysis Failed</h3>
              <p className="text-xs text-gray-400 text-center max-w-sm mt-2 leading-relaxed">
                {error}
              </p>
              <button
                onClick={() => runAnalysis(searchQuery)}
                className="mt-4 px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-xs hover:bg-white/10 transition-all"
              >
                Try Again
              </button>
            </div>
          )}

          {/* Welcome/Empty state */}
          {!result && !loading && !error && (
            <div className="flex-1 flex flex-col items-center justify-center p-12 bg-[#18181b]/10 border border-white/5 rounded-2xl min-h-[450px]">
              <div className="p-4 rounded-full bg-white/5 mb-4 border border-white/10">
                <Sparkles className="w-6 h-6 text-purple-400" />
              </div>
              <h3 className="font-semibold text-gray-200 text-sm">No Impact Analysis Yet</h3>
              <p className="text-xs text-gray-500 mt-2 text-center max-w-xs leading-relaxed">
                Select a function, class, or API route to see which parts of your codebase could be affected.
              </p>
            </div>
          )}

          {/* Results Panel */}
          {result && !loading && !error && (
            <div className="flex flex-col gap-6">
              
              {/* Fuzzy Matches Selection Block */}
              {result.fuzzy_matches.length > 0 && (
                <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4 flex flex-col gap-3">
                  <div className="flex gap-2 items-center">
                    <HelpCircle className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-semibold text-amber-300">Ambiguity: Multiple matches found for "{result.query}"</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {result.fuzzy_matches.slice(0, 4).map((f) => (
                      <button
                        key={f.node_id}
                        onClick={() => {
                          setSearchQuery(f.name)
                          runAnalysis(f.name)
                        }}
                        className="text-xs px-2.5 py-1.5 rounded-lg border border-amber-500/20 hover:border-amber-400 bg-amber-500/10 text-amber-300 flex items-center gap-1.5 transition-all"
                      >
                        <span className="font-semibold">{f.name}</span>
                        <NodeTypeBadge type={f.node_type} />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Resolved Target Header & Risk Score Card */}
              <div className="bg-[#18181b]/30 border border-white/5 rounded-2xl p-6 shadow-xl grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
                <div className="md:col-span-8">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-purple-500/10 border border-purple-500/20 text-purple-400">
                      {result.resolved_node_type || 'function'}
                    </span>
                    <span className="text-xs text-gray-500 font-mono">depth: {result.graph_traversal_depth}</span>
                  </div>
                  <h2 className="text-2xl font-bold text-white tracking-tight">{result.resolved_node_name || result.query}</h2>
                  <p className="text-xs text-gray-400 font-mono mt-1 max-w-[340px] truncate">{result.resolved_file_path || 'No path'}</p>
                  <p className="text-[10px] text-gray-600 font-mono mt-1.5">
                    Analyzed in {result.analysis_time_ms} ms · {result.evidence_count} evidence edges traversed
                  </p>
                </div>
                
                {/* Risk Circle Gauge */}
                <div className="md:col-span-4 flex flex-col items-center md:items-end justify-center">
                  <div className="flex flex-col items-center p-4 rounded-2xl bg-white/[0.02] border border-white/5 w-full md:w-36 text-center">
                    <span className="text-xs text-gray-500 mb-1">Risk Score</span>
                    <span className="text-4xl font-extrabold text-white tracking-tight">{result.risk.score}</span>
                    <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border mt-2 ${getRiskLevelColor(result.risk.level)}`}>
                      {result.risk.level}
                    </span>
                  </div>
                </div>
              </div>

              {/* Segment Tabs */}
              <div className="flex border-b border-white/5">
                {(['graph', 'affected', 'llm'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setActiveTab(t)}
                    className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider border-b-2 transition-all ${
                      activeTab === t
                        ? 'border-purple-500 text-purple-400'
                        : 'border-transparent text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    {t === 'graph' ? 'Blast Radius Map' : t === 'affected' ? 'Affected Assets' : 'Architect Explanation'}
                  </button>
                ))}
              </div>

              {/* Tab 1: Graph visualizer & Risk factors */}
              {activeTab === 'graph' && (
                <div className="flex flex-col gap-6 animate-fadeIn">
                  {/* SVG interactive graph */}
                  <BlastRadiusGraph
                    blastRadius={result.blast_radius}
                    resolvedNodeName={result.resolved_node_name}
                    resolvedNodeType={result.resolved_node_type}
                    directCallers={result.direct_callers}
                    indirectCallers={result.indirect_callers}
                    affectedApis={result.affected_apis}
                    affectedTables={result.affected_tables}
                    affectedServices={result.affected_services}
                    onSelectNode={(name) => {
                      setSearchQuery(name)
                      runAnalysis(name)
                    }}
                  />

                  {/* Risk breakdown calculations */}
                  <div className="bg-[#18181b]/30 border border-white/5 rounded-2xl p-5 shadow-xl">
                    <h3 className="font-semibold text-sm text-gray-200 mb-4 flex items-center gap-1.5">
                      <Code className="w-4 h-4 text-purple-400" />
                      Risk Calculation Breakdown ({result.scenario})
                    </h3>
                    <div className="space-y-4">
                      {result.risk.factors.map((f, idx) => (
                        <div key={idx} className="flex items-center justify-between text-xs py-1 border-b border-white/[0.02] last:border-0">
                          <div>
                            <span className="text-gray-300 font-medium">{f.factor}</span>
                            <span className="text-gray-600 font-mono ml-2">count: {f.count} × weight: {f.weight}</span>
                          </div>
                          <span className="font-mono text-purple-400 font-bold">+{f.contribution}</span>
                        </div>
                      ))}
                      <div className="pt-2 flex justify-between items-center text-sm font-bold text-white border-t border-white/10">
                        <span>Total Score (Clamped 0-100)</span>
                        <div className="flex items-center gap-3">
                          <div className="w-24 h-2 rounded-full bg-white/5 overflow-hidden">
                            <div className={`h-full ${getRiskGaugeColor(result.risk.score)}`} style={{ width: `${result.risk.score}%` }}></div>
                          </div>
                          <span className="font-mono text-base">{result.risk.score}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Affected lists */}
              {activeTab === 'affected' && (
                <div className="flex flex-col gap-6 animate-fadeIn">
                  
                  {/* Direct Callers */}
                  <ComponentSection
                    title={`Direct Callers (${result.direct_callers.length})`}
                    items={result.direct_callers}
                    icon={<ChevronRight className="w-4 h-4 text-purple-400" />}
                  />

                  {/* Indirect Callers */}
                  <ComponentSection
                    title={`Indirect Callers (${result.indirect_callers.length})`}
                    items={result.indirect_callers}
                    icon={<ChevronRight className="w-4 h-4 text-indigo-400" />}
                  />

                  {/* Affected APIs */}
                  <ComponentSection
                    title={`Affected API Routes (${result.affected_apis.length})`}
                    items={result.affected_apis}
                    icon={<Server className="w-4 h-4 text-pink-400" />}
                  />

                  {/* Affected DB Tables */}
                  <ComponentSection
                    title={`Database Table Dependents (${result.affected_tables.length})`}
                    items={result.affected_tables}
                    icon={<Database className="w-4 h-4 text-orange-400" />}
                  />

                  {/* Affected external services */}
                  <ComponentSection
                    title={`Service / Client Dependents (${result.affected_services.length})`}
                    items={result.affected_services}
                    icon={<Server className="w-4 h-4 text-yellow-400" />}
                  />

                  {/* Affected Auth */}
                  <ComponentSection
                    title={`Auth Middleware Dependents (${result.affected_auth.length})`}
                    items={result.affected_auth}
                    icon={<Key className="w-4 h-4 text-emerald-400" />}
                  />

                  {/* Affected Files List */}
                  <div className="bg-[#18181b]/30 border border-white/5 rounded-2xl p-5 shadow-xl">
                    <h3 className="font-semibold text-sm text-gray-200 mb-3 flex items-center gap-2">
                      <LayoutGrid className="w-4 h-4 text-purple-400" />
                      Affected Files ({result.affected_files.length})
                    </h3>
                    {result.affected_files.length === 0 ? (
                      <p className="text-xs text-gray-500">No files affected.</p>
                    ) : (
                      <div className="max-h-56 overflow-y-auto space-y-1.5 scrollbar-thin">
                        {result.affected_files.map((file, idx) => (
                          <div key={idx} className="text-xs text-gray-400 py-1.5 px-2.5 rounded bg-white/[0.02] hover:bg-white/[0.04] font-mono truncate">
                            {file}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Tab 3: LLM Explanation */}
              {activeTab === 'llm' && (
                <div className="flex flex-col gap-6 animate-fadeIn">
                  
                  {/* Executive Summary */}
                  <div className="bg-[#18181b]/30 border border-white/5 rounded-2xl p-5 shadow-xl">
                    <span className="text-[10px] uppercase font-bold text-purple-400 block mb-2 tracking-wider">Executive Summary</span>
                    <blockquote className="text-sm text-gray-300 italic border-l-2 border-purple-500 pl-4 py-1 leading-relaxed">
                      "{result.executive_summary}"
                    </blockquote>
                  </div>

                  {/* Business Impact list */}
                  <div className="bg-[#18181b]/30 border border-white/5 rounded-2xl p-5 shadow-xl">
                    <span className="text-[10px] uppercase font-bold text-pink-400 block mb-3 tracking-wider">Business Impact</span>
                    {result.business_impact.length === 0 ? (
                      <p className="text-xs text-gray-500">None detected.</p>
                    ) : (
                      <ul className="space-y-2.5">
                        {result.business_impact.map((bi, idx) => (
                          <li key={idx} className="text-xs text-gray-300 flex items-start gap-2.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-pink-500 mt-1.5 block shrink-0"></span>
                            <span className="leading-relaxed">{bi}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* Developer Action list */}
                  <div className="bg-[#18181b]/30 border border-white/5 rounded-2xl p-5 shadow-xl">
                    <span className="text-[10px] uppercase font-bold text-yellow-400 block mb-3 tracking-wider">Developer Tasks</span>
                    {result.developer_impact.length === 0 ? (
                      <p className="text-xs text-gray-500">None detected.</p>
                    ) : (
                      <ul className="space-y-2.5">
                        {result.developer_impact.map((di, idx) => (
                          <li key={idx} className="text-xs text-gray-300 flex items-start gap-2.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 mt-1.5 block shrink-0"></span>
                            <span className="leading-relaxed">{di}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* Recommended tests */}
                  <div className="bg-[#18181b]/30 border border-white/5 rounded-2xl p-5 shadow-xl">
                    <span className="text-[10px] uppercase font-bold text-cyan-400 block mb-3 tracking-wider">Recommended Tests</span>
                    {result.recommended_tests.length === 0 ? (
                      <p className="text-xs text-gray-500">None detected.</p>
                    ) : (
                      <ul className="space-y-2.5">
                        {result.recommended_tests.map((rt, idx) => (
                          <li key={idx} className="text-xs text-gray-300 flex items-start gap-2.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 mt-1.5 block shrink-0"></span>
                            <span className="leading-relaxed">{rt}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* Deployment advice & Rollback */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-[#18181b]/30 border border-white/5 rounded-2xl p-5 shadow-xl">
                      <span className="text-[10px] uppercase font-bold text-emerald-400 block mb-2 tracking-wider">Deployment Recommendation</span>
                      <p className="text-xs text-gray-300 leading-relaxed">
                        {result.deployment_recommendation || 'No recommendation provided.'}
                      </p>
                    </div>
                    <div className="bg-[#18181b]/30 border border-white/5 rounded-2xl p-5 shadow-xl">
                      <span className="text-[10px] uppercase font-bold text-orange-400 block mb-2 tracking-wider">Rollback Strategy</span>
                      <p className="text-xs text-gray-300 leading-relaxed">
                        {result.rollback_strategy || 'No rollback plan provided.'}
                      </p>
                    </div>
                  </div>
                </div>
              )}

            </div>
          )}
        </main>

        {/* COLUMN 3: Collapsible Dependency Tree (col-span-3) */}
        <aside className="lg:col-span-3 flex flex-col gap-6">
          {result && !loading && !error ? (
            <ImpactDependencyTree
              report={result}
              onSelectNode={(name) => {
                setSearchQuery(name)
                runAnalysis(name)
              }}
            />
          ) : (
            <div className="bg-[#18181b]/10 border border-white/5 rounded-2xl p-6 shadow-xl flex flex-col items-center justify-center text-center h-[300px]">
              <Layers className="w-5 h-5 text-gray-600 mb-2" />
              <span className="text-xs text-gray-500">Explore Code Dependencies</span>
            </div>
          )}
        </aside>

      </div>
    </div>
  )
}

function ComponentSection({
  title,
  items,
  icon,
}: {
  title: string
  items: AffectedItemV2[]
  icon: React.ReactNode
}) {
  const [expanded, setExpanded] = useState(false)
  if (items.length === 0) return null

  return (
    <div className="bg-[#18181b]/30 border border-white/5 rounded-2xl p-5 shadow-xl">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold text-sm text-gray-200 flex items-center gap-2">
          {icon}
          {title}
        </h3>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-purple-400 hover:text-purple-300 transition-colors font-semibold"
        >
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>

      {expanded && (
        <div className="max-h-60 overflow-y-auto space-y-2 scrollbar-thin pr-1">
          {items.map((item, idx) => (
            <div key={idx} className="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex flex-col gap-1.5">
              <div className="flex justify-between items-center">
                <span className="text-xs font-semibold text-white">{item.name}</span>
                <span className="text-[9px] uppercase font-bold text-gray-500 font-mono px-1.5 py-0.5 rounded bg-white/5 border border-white/5">
                  {item.node_type}
                </span>
              </div>
              <div className="text-[10px] text-gray-500 flex flex-wrap gap-1 items-center">
                <span className="font-semibold text-gray-400">Path:</span>
                <span className="font-mono text-gray-600 truncate max-w-[200px]">{item.file_path}</span>
                <span className="mx-1 text-gray-700">|</span>
                <span className="font-semibold text-gray-400">Path edges:</span>
                <span className="font-mono text-purple-500/80">{item.evidence.chain.join(' → ')}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

