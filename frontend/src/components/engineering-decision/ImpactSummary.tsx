import { Server, Layers, FileText, Database, Code, TestTube, Rocket, Workflow } from 'lucide-react'

interface Props {
  affectedAPIs: number
  affectedServices: number
  affectedFiles: number
  affectedClasses: number
  affectedTables: number
  affectedWorkflows: number
  estimatedTestFailures: number
  deploymentRisk: 'Low' | 'Medium' | 'High'
}

interface MetricCardProps {
  icon: React.ReactNode
  value: number | string
  label: string
  color: string
}

function MetricCard({ icon, value, label, color }: MetricCardProps) {
  return (
    <div className="bg-[#1a1a1a] rounded-lg p-4 hover:bg-[#2a2a2a] transition-colors cursor-pointer">
      <div className="flex items-center gap-2 mb-2">
        <div className={color}>{icon}</div>
        <span className="text-xs text-gray-500 uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white tabular-nums">{value}</div>
    </div>
  )
}

export default function ImpactSummary({
  affectedAPIs,
  affectedServices,
  affectedFiles,
  affectedClasses,
  affectedTables,
  affectedWorkflows,
  estimatedTestFailures,
  deploymentRisk
}: Props) {
  const getDeploymentRiskColor = (risk: string) => {
    switch (risk) {
      case 'High': return 'text-yellow-400'
      case 'Medium': return 'text-orange-400'
      case 'Low': return 'text-green-400'
      default: return 'text-gray-400'
    }
  }

  return (
    <div className="rounded-2xl border border-[#333] bg-[#1a1a1a] p-6">
      <h2 className="text-lg font-semibold text-white mb-4">What Breaks</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={<Server className="w-4 h-4 text-blue-400" />}
          value={affectedAPIs}
          label="APIs"
          color="text-blue-400"
        />
        <MetricCard
          icon={<Layers className="w-4 h-4 text-purple-400" />}
          value={affectedServices}
          label="Services"
          color="text-purple-400"
        />
        <MetricCard
          icon={<FileText className="w-4 h-4 text-green-400" />}
          value={affectedFiles}
          label="Files"
          color="text-green-400"
        />
        <MetricCard
          icon={<Code className="w-4 h-4 text-cyan-400" />}
          value={affectedClasses}
          label="Classes"
          color="text-cyan-400"
        />
        <MetricCard
          icon={<Database className="w-4 h-4 text-orange-400" />}
          value={affectedTables}
          label="Tables"
          color="text-orange-400"
        />
        <MetricCard
          icon={<Workflow className="w-4 h-4 text-pink-400" />}
          value={affectedWorkflows}
          label="Workflows"
          color="text-pink-400"
        />
        <MetricCard
          icon={<TestTube className="w-4 h-4 text-red-400" />}
          value={estimatedTestFailures}
          label="Test Failures"
          color="text-red-400"
        />
        <MetricCard
          icon={<Rocket className="w-4 h-4" />}
          value={deploymentRisk}
          label="Deployment Risk"
          color={getDeploymentRiskColor(deploymentRisk)}
        />
      </div>
    </div>
  )
}
