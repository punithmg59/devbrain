interface Props {
  level: 'low' | 'medium' | 'high' | 'critical'
  size?: 'sm' | 'md' | 'lg'
}

const STYLES: Record<Props['level'], string> = {
  low: 'bg-green-900/50 text-green-400 border border-green-700',
  medium: 'bg-yellow-900/50 text-yellow-400 border border-yellow-700',
  high: 'bg-orange-900/50 text-orange-400 border border-orange-700',
  critical: 'bg-red-900/50 text-red-400 border border-red-700',
}

const EMOJI: Record<Props['level'], string> = {
  low: '✅',
  medium: '⚠️',
  high: '🔶',
  critical: '🚨',
}

const SIZES: Record<NonNullable<Props['size']>, string> = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-3 py-1',
  lg: 'text-base px-4 py-1.5',
}

export default function RiskBadge({ level, size = 'md' }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium capitalize ${STYLES[level]} ${SIZES[size]}`}
    >
      <span>{EMOJI[level]}</span>
      {level}
    </span>
  )
}
