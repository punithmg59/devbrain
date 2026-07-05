import { XCircle, AlertTriangle, FileText, TestTube, Settings, Rocket } from 'lucide-react'
import type { ImpactSummary as ImpactSummaryType } from '../../types/simulation'

interface Props {
  impactSummary: ImpactSummaryType
}

export default function ImpactSummary({ impactSummary }: Props) {
  const sections = [
    {
      title: 'Critical Failures',
      icon: <XCircle className="w-5 h-5 text-red-400" />,
      color: 'border-red-500/30 bg-red-950/20',
      items: impactSummary.critical_failures,
      emptyMessage: 'No critical failures detected'
    },
    {
      title: 'Potential Runtime Errors',
      icon: <AlertTriangle className="w-5 h-5 text-orange-400" />,
      color: 'border-orange-500/30 bg-orange-950/20',
      items: impactSummary.potential_runtime_errors,
      emptyMessage: 'No runtime errors expected'
    },
    {
      title: 'Likely Build Errors',
      icon: <FileText className="w-5 h-5 text-yellow-400" />,
      color: 'border-yellow-500/30 bg-yellow-950/20',
      items: impactSummary.likely_build_errors,
      emptyMessage: 'No build errors expected'
    },
    {
      title: 'Likely Test Failures',
      icon: <TestTube className="w-5 h-5 text-purple-400" />,
      color: 'border-purple-500/30 bg-purple-950/20',
      items: impactSummary.likely_test_failures,
      emptyMessage: 'No test failures expected'
    },
    {
      title: 'Configuration Impact',
      icon: <Settings className="w-5 h-5 text-blue-400" />,
      color: 'border-blue-500/30 bg-blue-950/20',
      items: impactSummary.configuration_impact,
      emptyMessage: 'No configuration impact'
    }
  ]

  return (
    <div className="space-y-6">
      {/* Deployment Risk Card */}
      <div className={`rounded-xl border p-6 ${
        impactSummary.deployment_risk.includes('High')
          ? 'border-red-500/30 bg-red-950/20'
          : impactSummary.deployment_risk.includes('Medium')
          ? 'border-orange-500/30 bg-orange-950/20'
          : 'border-green-500/30 bg-green-950/20'
      }`}>
        <div className="flex items-center gap-3 mb-3">
          <Rocket className="w-5 h-5 text-white" />
          <h3 className="text-lg font-semibold text-white">Deployment Risk</h3>
        </div>
        <p className="text-gray-300">{impactSummary.deployment_risk}</p>
      </div>

      {/* Impact Sections */}
      <div className="grid gap-4">
        {sections.map((section) => (
          <div key={section.title} className={`rounded-xl border p-5 ${section.color}`}>
            <div className="flex items-center gap-3 mb-4">
              {section.icon}
              <h4 className="font-semibold text-white">{section.title}</h4>
              <span className="ml-auto text-sm text-gray-400">
                {section.items.length}
              </span>
            </div>
            
            {section.items.length === 0 ? (
              <p className="text-sm text-gray-500 italic">{section.emptyMessage}</p>
            ) : (
              <ul className="space-y-2">
                {section.items.map((item, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm text-gray-300">
                    <span className="text-gray-500 mt-1">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
