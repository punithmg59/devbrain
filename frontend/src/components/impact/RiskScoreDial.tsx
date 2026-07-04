import { useState, useEffect } from 'react'
import { Zap, Clock } from 'lucide-react'
import { RiskScore } from '../../types/impact'

interface Props {
  score: RiskScore
  blastRadius: number
  effortLabel: string
}

export function RiskScoreDial({ score, blastRadius, effortLabel }: Props) {
  const [animatedValue, setAnimatedValue] = useState(0)

  useEffect(() => {
    const duration = 300
    const start = 0
    const end = score.value
    const startTime = performance.now()

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)
      
      // Ease out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3)
      setAnimatedValue(start + (end - start) * easeOut)

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)
  }, [score.value])

  const getRiskColors = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical':
        return {
          text: 'text-red-400',
          stroke: 'stroke-red-500',
          bg: 'bg-red-950/40',
          border: 'border-red-500/30'
        }
      case 'high':
        return {
          text: 'text-amber-400',
          stroke: 'stroke-amber-500',
          bg: 'bg-amber-950/40',
          border: 'border-amber-500/30'
        }
      case 'medium':
        return {
          text: 'text-indigo-400',
          stroke: 'stroke-indigo-500',
          bg: 'bg-indigo-950/40',
          border: 'border-indigo-500/30'
        }
      case 'low':
        return {
          text: 'text-green-400',
          stroke: 'stroke-green-500',
          bg: 'bg-green-950/40',
          border: 'border-green-500/30'
        }
      default:
        return {
          text: 'text-gray-400',
          stroke: 'stroke-gray-500',
          bg: 'bg-gray-950/40',
          border: 'border-gray-500/30'
        }
    }
  }

  const colors = getRiskColors(score.level)
  const percentage = (score.value / 10) * 100
  const circumference = 2 * Math.PI * 80
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  return (
    <div className={`p-6 rounded-2xl ${colors.bg} border ${colors.border}`}>
      <div className="flex flex-col items-center">
        {/* SVG Circle Arc */}
        <div className="relative w-48 h-48">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 200 200">
            {/* Background circle */}
            <circle
              cx="100"
              cy="100"
              r="80"
              fill="none"
              stroke="currentColor"
              strokeWidth="12"
              className="text-white/5"
            />
            {/* Progress arc */}
            <circle
              cx="100"
              cy="100"
              r="80"
              fill="none"
              stroke="currentColor"
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className={`${colors.stroke} transition-all duration-300`}
            />
          </svg>
          
          {/* Centered number */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-5xl font-bold ${colors.text} transition-all`}>
              {animatedValue.toFixed(1)}
            </span>
            <span className={`text-sm font-bold uppercase tracking-wider mt-1 ${colors.text}`}>
              {score.level}
            </span>
          </div>
        </div>

        {/* Metric chips */}
        <div className="flex items-center gap-4 mt-6">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
            <Zap className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-white">{blastRadius} components</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
            <Clock className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-white">{effortLabel}</span>
          </div>
        </div>

        {/* Explanation */}
        <p className="text-xs text-gray-400 mt-4 text-center max-w-xs leading-relaxed">
          {score.explanation}
        </p>
      </div>
    </div>
  )
}
