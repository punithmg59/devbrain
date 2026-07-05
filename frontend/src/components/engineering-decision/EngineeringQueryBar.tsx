import { useState } from 'react'
import { Search, Play, X } from 'lucide-react'

interface Props {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  loading: boolean
  suggestions: string[]
}

export default function EngineeringQueryBar({
  value,
  onChange,
  onSubmit,
  loading,
  suggestions
}: Props) {
  const [showSuggestions, setShowSuggestions] = useState(false)

  const suggestionChips = [
    'Delete Service',
    'Rename Class',
    'Add Stripe',
    'Move API',
    'Refactor Module',
    'Explain Authentication'
  ]

  const handleSuggestionClick = (suggestion: string) => {
    onChange(suggestion)
    onSubmit()
  }

  return (
    <div className="space-y-4">
      {/* Query Input */}
      <div className="relative">
        <div className="relative">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">
            <Search className="w-5 h-5" />
          </div>
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !loading) {
                onSubmit()
              }
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="What are you planning to change?"
            className="w-full bg-gray-900/50 border border-gray-800 rounded-xl py-4 pl-12 pr-32 text-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all"
            disabled={loading}
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
            {value && (
              <button
                onClick={() => onChange('')}
                className="p-2 rounded-lg hover:bg-gray-800 text-gray-500 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onSubmit}
              disabled={loading || !value.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Analyzing
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Analyze
                </>
              )}
            </button>
          </div>
        </div>

        {/* Suggestions Dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <div className="absolute z-50 w-full mt-2 bg-gray-900 border border-gray-800 rounded-xl shadow-2xl overflow-hidden">
            {suggestions.slice(0, 6).map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestionClick(suggestion)}
                className="w-full px-4 py-3 text-left hover:bg-gray-800 transition-colors flex items-center gap-3 border-b border-gray-800 last:border-0"
              >
                <Search className="w-4 h-4 text-gray-500" />
                <span className="text-gray-300">{suggestion}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Suggestion Chips */}
      <div className="flex flex-wrap gap-2">
        {suggestionChips.map((chip, idx) => (
          <button
            key={idx}
            onClick={() => handleSuggestionClick(chip)}
            className="px-4 py-2 rounded-lg border border-gray-800 bg-gray-900/30 text-gray-400 hover:text-white hover:border-gray-700 hover:bg-gray-800/50 text-sm transition-all"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  )
}
