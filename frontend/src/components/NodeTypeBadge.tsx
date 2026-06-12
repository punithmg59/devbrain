export default function NodeTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    function: 'bg-blue-900/40 text-blue-400 border-blue-700/40',
    class: 'bg-purple-900/40 text-purple-400 border-purple-700/40',
    method: 'bg-teal-900/40 text-teal-400 border-teal-700/40',
    api_route: 'bg-green-900/40 text-green-400 border-green-700/40',
  }
  return (
    <span
      className={`px-1.5 py-0.5 text-[10px] font-medium rounded border ${
        colors[type] ?? 'bg-gray-800 text-gray-400 border-gray-700'
      }`}
    >
      {type}
    </span>
  )
}
