import { Brain } from 'lucide-react'

interface Props {
  reasoning: string[]
}

export default function DecisionSummary({ reasoning }: Props) {
  if (!reasoning || reasoning.length === 0) {
    return null
  }

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900/30 p-8 mb-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-blue-500/10">
          <Brain className="w-5 h-5 text-blue-400" />
        </div>
        <h2 className="text-xl font-semibold text-white">Why DevBrain Reached This Decision</h2>
      </div>
      <ul className="space-y-4">
        {reasoning.map((reason, i) => (
          <li key={i} className="flex items-start gap-4 text-gray-300 text-lg leading-relaxed">
            <div className="w-2 h-2 rounded-full bg-purple-400 mt-2.5 shrink-0" />
            <span>{reason}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
