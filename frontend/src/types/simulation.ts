export type ChangeType = 'delete' | 'rename' | 'move' | 'extract' | 'add'

export type RiskLevel = 'safe' | 'moderate' | 'high' | 'critical'

export interface SimulationStep {
  id: string
  description: string
  component: string
  componentType: string
  impact: 'critical' | 'error' | 'warning' | 'info'
  depth: number
}

export interface CascadeChain {
  id: string
  startComponent: string
  endComponent: string
  steps: SimulationStep[]
  severity: 'critical' | 'high' | 'medium' | 'low'
}

export interface ImpactMetrics {
  affected_apis: number
  affected_services: number
  affected_classes: number
  affected_files: number
  affected_database_tables: number
  affected_workflows: number
  critical_dependency_chains: number
  estimated_blast_radius: number
}

export interface ImpactSummary {
  critical_failures: string[]
  potential_runtime_errors: string[]
  likely_build_errors: string[]
  likely_test_failures: string[]
  configuration_impact: string[]
  deployment_risk: string
}

export interface SimulationResult {
  change_type: ChangeType
  target_component: string
  target_type: string
  risk_level: RiskLevel
  confidence: number
  impact_metrics: ImpactMetrics
  impact_summary: ImpactSummary
  timeline: SimulationStep[]
  cascade_chains: CascadeChain[]
  affected_components: Array<{
    id: string
    name: string
    type: string
    file: string
    depth: number
    critical: boolean
  }>
}

export interface SimulationRequest {
  repo_id: string
  change_type: ChangeType
  target_name: string
  target_type?: string
  max_depth?: number
}
