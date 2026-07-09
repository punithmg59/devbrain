import { useState, KeyboardEvent } from 'react'
import { Send, Sparkles } from 'lucide-react'

interface Props {
  onAnalyze: (query: string) => void
  isLoading?: boolean
}

const SUGGESTIONS = [
  'Delete AuthService',
  'Rename UserService',
  'Move PaymentController',
  'Add Stripe Integration',
  'Extract NotificationService',
  'Explain Authentication',
  'Find Order Workflow'
]

export default function QuestionBar({ onAnalyze, isLoading = false }: Props) {
  const [query, setQuery] = useState('')
  const [filteredSuggestions, setFilteredSuggestions] = useState<string[]>(SUGGESTIONS)

  const handleInputChange = (value: string) => {
    setQuery(value)
    if (value) {
      const filtered = SUGGESTIONS.filter(s => 
        s.toLowerCase().includes(value.toLowerCase())
      )
      setFilteredSuggestions(filtered)
    } else {
      setFilteredSuggestions(SUGGESTIONS)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (query.trim() && !isLoading) {
        onAnalyze(query.trim())
      }
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion)
    setFilteredSuggestions([])
    onAnalyze(suggestion)
  }

  const handleSubmit = () => {
    if (query.trim() && !isLoading) {
      onAnalyze(query.trim())
    }
  }

  return (
    <div className="w-full max-w-[90%] mx-auto space-y-4">
      <div className="relative">
        <textarea
          value={query}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What change are you planning?"
          rows={1}
          className="w-full bg-[#1a1a1a] border border-[#333] rounded-xl px-6 py-4 text-white placeholder-gray-500 resize-none focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all"
          style={{ minHeight: '56px', maxHeight: '120px' }}
          disabled={isLoading}
          aria-label="What change are you planning?"
        />
        
        <button
          onClick={handleSubmit}
          disabled={!query.trim() || isLoading}
          className="absolute right-3 bottom-3 p-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
          aria-label="Analyze change"
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>

      {!query && filteredSuggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <Sparkles className="w-4 h-4 text-purple-400 mt-1" />
          {filteredSuggestions.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => handleSuggestionClick(suggestion)}
              className="px-4 py-2 bg-[#1a1a1a] border border-[#333] hover:border-purple-500 text-gray-400 hover:text-white rounded-lg text-sm transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
