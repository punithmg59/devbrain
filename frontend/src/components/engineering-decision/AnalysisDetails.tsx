import { useState } from 'react'
import { ChevronDown, ChevronUp, Clock, Code2, Target, Calendar } from 'lucide-react'

interface Props {
  executionTime: string
  pipelineTimings: Record<string, number>
  intent: string
  confidence: number
  repositoryVersion: string
  analysisTimestamp: string
}

export default function AnalysisDetails({
  executionTime,
  pipelineTimings,
  intent,
  confidence,
  repositoryVersion,
  analysisTimestamp
}: Props) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900/30 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-8 py-5 hover:bg-gray-800/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gray-800">
            <Clock className="w-5 h-5 text-gray-400" />
          </div>
          <span className="font-semibold text-white text-lg">Analysis Details</span>
          <span className="text-sm text-gray-500">Technical execution information</span>
        </div>
        {isOpen ? <ChevronUp className="w-5 h-5 text-gray-500" /> : <ChevronDown className="w-5 h-5 text-gray-500" />}
      </button>

      {isOpen && (
        <div className="px-8 pb-8 space-y-6">
          {/* Intent */}
          <div className="bg-gray-800/50 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-purple-400" />
              <span className="font-semibold text-white">Analysis Intent</span>
            </div>
            <p className="text-sm text-gray-300">{intent}</p>
          </div>

          {/* Confidence */}
          <div className="bg-gray-800/50 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-green-400" />
              <span className="font-semibold text-white">Confidence Score</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-3xl font-bold text-green-400">{Math.round(confidence * 100)}%</div>
              <div className="text-sm text-gray-400">
                {confidence > 0.9 ? 'Very High' : confidence > 0.7 ? 'High' : confidence > 0.5 ? 'Medium' : 'Low'} confidence in analysis
              </div>
            </div>
          </div>

          {/* Repository Version */}
          <div className="bg-gray-800/50 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Code2 className="w-4 h-4 text-blue-400" />
              <span className="font-semibold text-white">Repository Version</span>
            </div>
            <p className="text-sm text-gray-300 font-mono">{repositoryVersion}</p>
          </div>

          {/* Analysis Timestamp */}
          <div className="bg-gray-800/50 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Calendar className="w-4 h-4 text-yellow-400" />
              <span className="font-semibold text-white">Analysis Timestamp</span>
            </div>
            <p className="text-sm text-gray-300">{analysisTimestamp}</p>
          </div>

          {/* Execution Time */}
          <div className="bg-gray-800/50 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Clock className="w-4 h-4 text-cyan-400" />
              <span className="font-semibold text-white">Total Execution Time</span>
            </div>
            <p className="text-sm text-gray-300">{executionTime}</p>
          </div>

          {/* Pipeline Timings */}
          {Object.keys(pipelineTimings).length > 0 && (
            <div className="bg-gray-800/50 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="w-4 h-4 text-orange-400" />
                <span className="font-semibold text-white">Pipeline Timings</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(pipelineTimings).map(([key, value]) => (
                  <div key={key}>
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
                      {key.replace('_ms', '').replace(/_/g, ' ')}
                    </div>
                    <div className="text-sm text-gray-300 font-mono">{value} ms</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
