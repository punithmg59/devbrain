import { useState, useEffect } from 'react'
import { X, Search, Globe, Building2, Code2, GitBranch, Layers, FileText, ChevronRight } from 'lucide-react'
import { repoService } from '../services/repoService'
import CallersDependencyTree from './CallersDependencyTree'
import type { CallersResponse, CallerNode, CallerFilter } from '../types/callers'

interface Props {
  isOpen: boolean
  onClose: () => void
  repoId: string
  nodeId: string
  onNavigateToFile?: (file: string, line?: number) => void
}

export default function CallersDrawer({ isOpen, onClose, repoId, nodeId, onNavigateToFile }: Props) {
  const [data, setData] = useState<CallersResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filter, setFilter] = useState<CallerFilter>('all')

  useEffect(() => {
    if (isOpen && repoId && nodeId) {
      loadCallers()
    }
  }, [isOpen, repoId, nodeId])

  const loadCallers = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await repoService.getCallers(repoId, nodeId)
      setData(result)
    } catch (err) {
      setError('Failed to load callers')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const filteredCallers = data?.callers.filter(caller => {
    // Filter by type
    if (filter !== 'all' && caller.type !== filter) {
      return false
    }
    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        caller.name.toLowerCase().includes(query) ||
        caller.file.toLowerCase().includes(query)
      )
    }
    return true
  }) ?? []

  const handleCallerClick = (caller: CallerNode) => {
    if (onNavigateToFile && caller.file) {
      onNavigateToFile(caller.file, caller.start_line)
    }
  }

  const getFilterIcon = (filterType: CallerFilter) => {
    switch (filterType) {
      case 'api_route': return <Globe className="w-4 h-4" />
      case 'service': return <Building2 className="w-4 h-4" />
      case 'class': return <Code2 className="w-4 h-4" />
      case 'function': return <Layers className="w-4 h-4" />
      case 'workflow': return <GitBranch className="w-4 h-4" />
      default: return <FileText className="w-4 h-4" />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'api_route': return 'text-green-400'
      case 'service': return 'text-blue-400'
      case 'class': return 'text-purple-400'
      case 'function':
      case 'method': return 'text-yellow-400'
      case 'workflow': return 'text-cyan-400'
      default: return 'text-gray-400'
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Drawer */}
      <div className="relative ml-auto h-full w-[600px] bg-[#09090b] border-l border-gray-800 shadow-2xl flex flex-col animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div>
            <h2 className="text-xl font-semibold text-white">All Callers</h2>
            {data && (
              <p className="text-sm text-gray-500 mt-1">
                {data.target.name} • {data.summary.total_callers} callers
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              Loading callers...
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-red-400">
              {error}
            </div>
          ) : data ? (
            <div className="p-6 space-y-6">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-2xl font-bold text-white">{data.summary.total_callers}</div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider">Total Callers</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-2xl font-bold text-orange-400">{data.summary.critical_callers}</div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider">Critical</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-2xl font-bold text-green-400">{data.summary.api_routes}</div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider">API Routes</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-2xl font-bold text-blue-400">{data.summary.services}</div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider">Services</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-2xl font-bold text-purple-400">{data.summary.classes}</div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider">Classes</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-2xl font-bold text-yellow-400">{data.summary.functions}</div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider">Functions</div>
                </div>
              </div>

              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search callers..."
                  className="w-full bg-gray-900/50 border border-gray-800 rounded-lg py-3 pl-10 pr-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50"
                />
              </div>

              {/* Filters */}
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setFilter('all')}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    filter === 'all'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:text-white'
                  }`}
                >
                  All ({data.summary.total_callers})
                </button>
                <button
                  onClick={() => setFilter('api_route')}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    filter === 'api_route'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:text-white'
                  }`}
                >
                  <Globe className="w-3 h-3" />
                  API ({data.summary.api_routes})
                </button>
                <button
                  onClick={() => setFilter('service')}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    filter === 'service'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:text-white'
                  }`}
                >
                  <Building2 className="w-3 h-3" />
                  Services ({data.summary.services})
                </button>
                <button
                  onClick={() => setFilter('class')}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    filter === 'class'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:text-white'
                  }`}
                >
                  <Code2 className="w-3 h-3" />
                  Classes ({data.summary.classes})
                </button>
                <button
                  onClick={() => setFilter('function')}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    filter === 'function'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:text-white'
                  }`}
                >
                  <Layers className="w-3 h-3" />
                  Functions ({data.summary.functions})
                </button>
              </div>

              {/* Dependency Tree */}
              <CallersDependencyTree target={data.target} callers={data.callers} maxDepth={3} />

              {/* Caller List */}
              <div className="space-y-2">
                {filteredCallers.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No callers match your filters
                  </div>
                ) : (
                  filteredCallers.map((caller) => (
                    <button
                      key={caller.id}
                      onClick={() => handleCallerClick(caller)}
                      className="w-full text-left p-4 rounded-lg border border-gray-800 bg-gray-900/30 hover:border-gray-700 hover:bg-gray-800/50 transition-all group"
                    >
                      <div className="flex items-start gap-3">
                        <div className={`p-2 rounded-lg bg-gray-800 ${getTypeColor(caller.type)}`}>
                          {getFilterIcon(caller.type as CallerFilter)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold text-white truncate">{caller.name}</span>
                            {caller.critical && (
                              <span className="px-2 py-0.5 text-xs font-medium bg-orange-500/20 text-orange-400 rounded-full shrink-0">
                                Critical
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-gray-500 truncate mb-2">{caller.file}</div>
                          <div className="flex items-center gap-3 text-xs text-gray-600">
                            <span className="capitalize">{caller.type}</span>
                            <span>•</span>
                            <span>Depth {caller.depth}</span>
                          </div>
                        </div>
                        <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-purple-400 transition-colors shrink-0 mt-1" />
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
