import { useState, useEffect, useRef } from 'react'
import { Search, X, Loader2 } from 'lucide-react'
import { NodeSearchResult } from '../../types/impact'
import { impactService } from '../../services/impactService'

interface Props {
  repoId: string
  onAnalyze: (node: NodeSearchResult) => void
  isAnalyzing: boolean
}

export function ImpactSearchBar({ repoId, onAnalyze, isAnalyzing }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<NodeSearchResult[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [selected, setSelected] = useState<NodeSearchResult | null>(null)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const [loading, setLoading] = useState(false)
  
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    
    if (query.length < 2) {
      setResults([])
      setShowDropdown(false)
      return
    }

    setLoading(true)
    debounceRef.current = setTimeout(async () => {
      try {
        const data = await impactService.searchImpactNodes(repoId, query)
        setResults(data)
        setShowDropdown(true)
        setHighlightedIndex(-1)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 250)

    return () => clearTimeout(debounceRef.current)
  }, [query, repoId])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setHighlightedIndex(prev => 
          prev < results.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setHighlightedIndex(prev => prev > 0 ? prev - 1 : -1)
        break
      case 'Escape':
        setShowDropdown(false)
        break
      case 'Enter':
        e.preventDefault()
        if (highlightedIndex >= 0 && results[highlightedIndex]) {
          handleSelect(results[highlightedIndex])
        }
        break
    }
  }

  const handleSelect = (node: NodeSearchResult) => {
    setSelected(node)
    setQuery(node.name)
    setShowDropdown(false)
  }

  const handleClear = () => {
    setQuery('')
    setSelected(null)
    setResults([])
    setShowDropdown(false)
    inputRef.current?.focus()
  }

  const handleAnalyze = () => {
    if (selected) {
      onAnalyze(selected)
    }
  }

  const getTypeBadgeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'function': return 'bg-indigo-600/20 text-indigo-400 border-indigo-500/30'
      case 'class': return 'bg-purple-600/20 text-purple-400 border-purple-500/30'
      case 'api_route': return 'bg-green-600/20 text-green-400 border-green-500/30'
      case 'database_table': return 'bg-amber-600/20 text-amber-400 border-amber-500/30'
      case 'service': return 'bg-blue-600/20 text-blue-400 border-blue-500/30'
      default: return 'bg-gray-600/20 text-gray-400 border-gray-500/30'
    }
  }

  const getBlastRadiusColor = (radius: number) => {
    if (radius > 20) return 'bg-red-600/20 text-red-400 border-red-500/30'
    if (radius > 5) return 'bg-amber-600/20 text-amber-400 border-amber-500/30'
    return 'bg-green-600/20 text-green-400 border-green-500/30'
  }

  return (
    <div className="relative w-full">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setShowDropdown(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search function, class, service, API, or table..."
          className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-10 py-3 text-white placeholder-white/30 focus:border-indigo-500 focus:outline-none transition-colors"
        />
        {selected && (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {showDropdown && (results.length > 0 || loading) && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-2 bg-[#161B22] border border-white/10 rounded-lg shadow-xl max-h-80 overflow-y-auto"
        >
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
            </div>
          ) : results.length === 0 ? (
            <div className="py-4 text-center text-gray-500 text-sm">No results found</div>
          ) : (
            results.map((node, index) => (
              <button
                key={node.id}
                onClick={() => handleSelect(node)}
                className={`w-full px-4 py-3 hover:bg-white/5 cursor-pointer flex items-center gap-3 border-b border-white/5 last:border-0 transition-colors ${
                  index === highlightedIndex ? 'bg-white/5' : ''
                }`}
              >
                <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getTypeBadgeColor(node.node_type)}`}>
                  {node.node_type}
                </span>
                <span className="flex-1 text-left text-sm font-medium truncate">{node.name}</span>
                <span className="text-xs text-gray-500 truncate max-w-32">{node.file_path}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getBlastRadiusColor(node.blast_radius ?? 0)}`}>
                  {node.blast_radius ?? 0}
                </span>
              </button>
            ))
          )}
        </div>
      )}

      {selected && (
        <button
          onClick={handleAnalyze}
          disabled={isAnalyzing}
          className="mt-3 w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              Analyze Impact →
            </>
          )}
        </button>
      )}
    </div>
  )
}
