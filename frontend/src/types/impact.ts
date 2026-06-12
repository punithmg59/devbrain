export interface ImpactNode {
  id: string
  name: string
  node_type: string
  file_path: string
  start_line: number | null
  end_line: number | null
  depth: number
  direction: 'downstream' | 'upstream'
  risk_score: number
  edge_type: string
  inclusion_reason?: string | null
  risk_tier?: string | null
  http_method?: string | null
  route_path?: string | null
}

export interface ImpactFile {
  file_path: string
  file_name: string
  affected_functions: string[]
  risk_level: 'low' | 'medium' | 'high' | 'critical'
}

export interface AffectedAPI {
  method: string
  path: string
  node_id: string
  name: string
  file_path: string
  inclusion_reason: string
}

export interface TestRecommendation {
  title: string
  priority: 'critical' | 'high' | 'medium'
  reason: string
  evidence?: string | null
}

export interface DeploymentAdvice {
  summary: string
  recommendations: string[]
  monitoring: string[]
  rollback_trigger?: string | null
}

export interface GraphNode {
  id: string
  name: string
  node_type: string
  file_path: string
  risk_tier: string
  is_source: boolean
  depth: number
  confidence?: number
}

export interface GraphEdge {
  from_id: string
  to_id: string
  edge_type: string
  confidence?: number
}

export interface ImpactGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface ExactDependencyItem {
  id: string
  name: string
  node_type: string
  file_path: string
  confidence: number
}

export interface ExactDependencies {
  level_1_direct: ExactDependencyItem[]
  level_1_incoming: ExactDependencyItem[]
  level_2_indirect: ExactDependencyItem[]
  level_3_workflow: ExactDependencyItem[]
  database_dependencies: ExactDependencyItem[]
  api_dependencies: ExactDependencyItem[]
  file_dependencies: string[]
}

export interface ImpactGraphResponse {
  repo_id: string
  source_node_id: string
  exact_dependencies: ExactDependencies
  graph: ImpactGraph
}

export interface ResolvedEntity {
  id: string
  name: string
  node_type: string
  file_path: string
  match_reason: string
  score: number
}

export interface BlastRadius {
  functions: number
  classes: number
  api_routes: number
  files: number
  max_depth: number
  total_nodes: number
  verified_edges: number
  scenario: string
  workflows_impacted?: number
  services_impacted?: number
  journeys_impacted?: number
  blast_radius_score?: number
  risk_category?: string
  estimated_users_impacted?: string
  deployment_risk?: string
  critical_paths_impacted?: string[]
  score_breakdown?: ScoreComponent[]
}

export interface CriticalPathSummary {
  id: string
  name: string
  criticality: string
  description?: string | null
  impacted_node_names: string[]
}

export interface JourneyImpactItem {
  journey_id: string
  journey_name: string
  severity: string
  user_impact: string
  affected_workflows: string[]
}

export interface BusinessImpactItem {
  category: string
  impact_label: string
  severity: string
  reason: string
  journey_name?: string | null
}

export interface BlastRadiusReport {
  blast_radius_score: number
  risk_category: string
  functions_impacted: number
  classes_impacted: number
  files_impacted: number
  apis_impacted: number
  workflows_impacted: number
  services_impacted: number
  journeys_impacted: number
  estimated_users_impacted: string
  deployment_risk: string
  critical_paths_impacted: CriticalPathSummary[]
  service_names: string[]
  journey_names: string[]
  workflow_names: string[]
  score_breakdown: ScoreComponent[]
  summary: string
  journey_impacts: JourneyImpactItem[]
  business_impacts: BusinessImpactItem[]
}

export interface WorkflowImpact {
  workflow_id: string
  workflow_name: string
  user_impact: string
  evidence_nodes: string[]
  evidence_source: string
  service_name?: string | null
  severity?: string
  confidence?: number
  confidence_percent?: number
  evidence_chain?: string | null
  affected_apis?: string[]
  recommended_tests?: string[]
  criticality?: string
}

export interface PrimaryWorkflow {
  id: string
  name: string
  confidence: number
  confidence_percent?: number
  service_name?: string | null
}

export interface WorkflowEvidenceItem {
  workflow_id: string
  workflow_name: string
  chain_summary: string
  confidence_percent: number
  steps: { label: string; step_type: string }[]
}

export interface ScoreComponent {
  name: string
  points: number
  max_points: number
  evidence: string
}

export interface RiskScoreBreakdown {
  total: number
  tier: string
  components: ScoreComponent[]
}

export interface ConfidenceBreakdown {
  total: number
  components: ScoreComponent[]
}

export interface ChangeRecommendation {
  decision: string
  should_proceed: boolean
  label: string
}

export interface RolloutStrategy {
  strategy: string
  steps: string[]
  feature_flag_recommended?: boolean
  canary_recommended?: boolean
}

export interface RollbackStrategy {
  strategy: string
  steps: string[]
  trigger?: string | null
}

export interface ImpactResult {
  query: string
  resolved_query: string
  resolution_confidence: number
  matched_entities: ResolvedEntity[]
  source_node: Record<string, unknown> | null
  impacted_nodes: ImpactNode[]
  impacted_files: ImpactFile[]
  graph: ImpactGraph | null
  risk_level: string
  risk_score: number
  risk_score_100: number
  confidence: number
  executive_summary: string
  why_this_matters: string
  blast_radius: BlastRadius
  business_impact: string[]
  engineering_impact: string[]
  developer_impact: string[]
  workflow_impact: WorkflowImpact[]
  primary_workflow?: PrimaryWorkflow | null
  affected_journeys?: string[]
  workflow_evidence?: WorkflowEvidenceItem[]
  workflow_confidence?: number
  user_impact: string[]
  affected_systems: string[]
  affected_apis: AffectedAPI[]
  explanation: string
  risk_analysis: string
  ai_recommendation: string
  staff_engineer_recommendation: string
  recommended_tests: TestRecommendation[]
  deployment_advice: DeploymentAdvice | null
  rollout_strategy: RolloutStrategy
  rollback_strategy: RollbackStrategy
  monitoring_plan: string[]
  risk_score_breakdown: RiskScoreBreakdown
  confidence_breakdown: ConfidenceBreakdown
  change_recommendation: ChangeRecommendation
  pr_checklist: string[]
  qa_checklist: string[]
  rollback_plan: string[]
  total_affected_functions: number
  total_affected_files: number
  analysis_time_ms: number
  warning?: string | null
  scenario: string
  blast_radius_report?: BlastRadiusReport | null
  journey_impact_items?: JourneyImpactItem[]
  business_impact_items?: BusinessImpactItem[]
  exact_dependencies?: ExactDependencies | null
  version?: string
}

export type ChangeScenario = 'modify' | 'delete' | 'refactor'

export interface ImpactRequest {
  query: string
  max_depth?: number
  direction?: 'both' | 'downstream' | 'upstream'
  natural_language?: boolean
  scenario?: ChangeScenario
}

export interface ImpactSearchNode {
  id: string
  name: string
  node_type: string
  file_path: string
}

// ── Impact Radar V2 Types ──────────────────────────

export interface ImpactEvidenceV2 {
  source: string
  target: string
  edge_type: string
  depth: number
  chain: string[]
}

export interface AffectedItemV2 {
  name: string
  node_type: string
  file_path: string
  evidence: ImpactEvidenceV2
}

export interface BlastRadiusV2 {
  direct_dependents: number
  indirect_dependents: number
  api_impact: number
  database_impact: number
  service_impact: number
  file_impact: number
  auth_impact: number
  class_impact: number
  total_nodes_affected: number
  cycles_detected: number
}

export interface RiskFactorV2 {
  factor: string
  count: number
  weight: number
  contribution: number
}

export interface RiskResultV2 {
  score: number // 0-100
  level: string // Safe | Low | Medium | High | Critical
  scenario: string
  factors: RiskFactorV2[]
}

export interface FuzzyMatchV2 {
  node_id: string
  name: string
  node_type: string
  file_path: string
  score: number
}

export interface ImpactReportV2 {
  query: string
  scenario: string
  resolved_node_id: string | null
  resolved_node_name: string | null
  resolved_node_type: string | null
  resolved_file_path: string | null
  fuzzy_matches: FuzzyMatchV2[]

  blast_radius: BlastRadiusV2
  risk: RiskResultV2

  direct_callers: AffectedItemV2[]
  indirect_callers: AffectedItemV2[]
  affected_apis: AffectedItemV2[]
  affected_tables: AffectedItemV2[]
  affected_services: AffectedItemV2[]
  affected_files: string[]
  affected_classes: AffectedItemV2[]
  affected_auth: AffectedItemV2[]

  executive_summary: string
  business_impact: string[]
  developer_impact: string[]
  recommended_tests: string[]
  deployment_recommendation: string
  rollback_strategy: string

  analysis_time_ms: number
  graph_traversal_depth: number
  evidence_count: number
}

