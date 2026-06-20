import API from "./authService";

export interface CriticalComponent {
  node_id: string;
  name: string;
  node_type: string;
  file_path: string | null;
  influence_score: number;
  fan_in: number;
  fan_out: number;
  dependents_count: number;
  reason: string;
}

export interface CriticalComponentsResponse {
  repo_id: string;
  components: CriticalComponent[];
  total_nodes: number;
  total_edges: number;
}

export interface Bottleneck {
  node_id: string;
  name: string;
  node_type: string;
  file_path: string | null;
  bottleneck_type: string;
  severity: "critical" | "high" | "medium";
  metric_value: number;
  threshold: number;
  description: string;
}

export interface BottlenecksResponse {
  repo_id: string;
  bottlenecks: Bottleneck[];
  total_god_services: number;
  total_oversized_modules: number;
  total_fan_explosions: number;
}

export interface CyclicDependency {
  cycle_id: number;
  nodes: { node_id: string; name: string; node_type: string }[];
  length: number;
  severity: "critical" | "high" | "medium";
}

export interface CouplingPair {
  node_a_id: string;
  node_a_name: string;
  node_b_id: string;
  node_b_name: string;
  shared_edges: number;
  coupling_score: number;
  recommendation: string;
}

export interface ArchitectureViolation {
  violation_type: string;
  description: string;
  severity: "critical" | "high" | "medium";
  involved_nodes: { node_id: string; name: string; node_type: string }[];
}

export interface RefactorOpportunitiesResponse {
  repo_id: string;
  cyclic_dependencies: CyclicDependency[];
  tightly_coupled: CouplingPair[];
  violations: ArchitectureViolation[];
  total_issues: number;
}

export interface ImpactedEntity {
  node_id: string;
  name: string;
  node_type: string;
  file_path: string | null;
  impact_path_length: number;
}

export interface ChangeRiskReport {
  repo_id: string;
  target_node_id: string;
  target_node_name: string;
  risk_score: number;
  risk_level: "critical" | "high" | "medium" | "low";
  impacted_nodes: ImpactedEntity[];
  impacted_apis: ImpactedEntity[];
  impacted_services: ImpactedEntity[];
  impacted_databases: ImpactedEntity[];
  total_impacted: number;
  summary: string;
}

export interface Finding {
  rank: number;
  title: string;
  category: "critical_component" | "bottleneck" | "coupling" | "risk" | "health";
  severity: "critical" | "high" | "medium" | "info";
  description: string;
  related_node_ids: string[];
  metric_name: string;
  metric_value: number;
  recommendation: string;
}

export interface FindingsResponse {
  repo_id: string;
  findings: Finding[];
  generated_at: string;
}

export interface IntelligenceDashboard {
  repo_id: string;
  architecture_score: number;
  risk_score: number;
  architecture_grade: "A" | "B" | "C" | "D" | "F";
  total_nodes: number;
  total_edges: number;
  critical_components: CriticalComponent[];
  bottlenecks: Bottleneck[];
  refactor_suggestions: Finding[];
  top_findings: Finding[];
}

export const intelligenceService = {
  getCriticalComponents: async (repoId: string): Promise<CriticalComponentsResponse> => {
    const res = await API.get(`/api/repos/${repoId}/architecture/intelligence/critical`);
    return res.data;
  },
  getBottlenecks: async (repoId: string): Promise<BottlenecksResponse> => {
    const res = await API.get(`/api/repos/${repoId}/architecture/intelligence/bottlenecks`);
    return res.data;
  },
  getRefactorOpportunities: async (repoId: string): Promise<RefactorOpportunitiesResponse> => {
    const res = await API.get(`/api/repos/${repoId}/architecture/intelligence/refactor`);
    return res.data;
  },
  getChangeRisk: async (repoId: string, nodeId: string): Promise<ChangeRiskReport> => {
    const res = await API.get(`/api/repos/${repoId}/architecture/intelligence/risk/${nodeId}`);
    return res.data;
  },
  getFindings: async (repoId: string): Promise<FindingsResponse> => {
    const res = await API.get(`/api/repos/${repoId}/architecture/intelligence/findings`);
    return res.data;
  },
  getDashboard: async (repoId: string): Promise<IntelligenceDashboard> => {
    const res = await API.get(`/api/repos/${repoId}/architecture/intelligence/dashboard`);
    return res.data;
  },
};
