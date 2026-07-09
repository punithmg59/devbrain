import { useState } from 'react'
import { ChevronDown, ChevronUp, FileText } from 'lucide-react'

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
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 rounded-xl border border-[#333] bg-[#1a1a1a] hover:bg-[#2a2a2a] transition-colors"
      >
        <div className="flex items-center gap-3">
          <FileText className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-500">Analysis Details</span>
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
      </button>

      {isOpen && (
        <div className="rounded-xl border border-[#333] bg-[#1a1a1a] p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-500 mb-1">Intent</div>
              <div className="text-white">{intent}</div>
            </div>
            <div>
              <div className="text-gray-500 mb-1">Execution Time</div>
              <div className="text-white">{executionTime}s</div>
            </div>
            <div>
              <div className="text-gray-500 mb-1">Confidence</div>
              <div className="text-white">{Math.round(confidence * 100)}%</div>
            </div>
            <div>
              <div className="text-gray-500 mb-1">Repository Version</div>
              <div className="text-white">{repositoryVersion}</div>
            </div>
            <div>
              <div className="text-gray-500 mb-1">Analysis Timestamp</div>
              <div className="text-white">{new Date(analysisTimestamp).toLocaleString()}</div>
            </div>
            <div>
              <div className="text-gray-500 mb-1">Pipeline Timings</div>
              <div className="text-white">{Object.keys(pipelineTimings).length} stages</div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
