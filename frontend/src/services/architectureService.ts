/**
 * Architecture API service — reads the existing repository graph
 * (nodes / edges / repo_files). No AI, no explanation generation.
 */

import API from "./authService";

export interface ArchitectureOverview {
  frontend_components: number;
  backend_services: number;
  api_routes: number;
  database_tables: number;
  classes: number;
  functions: number;
  external_apis: number;
  total_files: number;
  total_dependencies: number;
}

export interface ArchNodeSummary {
  id: string;
  name: string;
  node_type: string;
  full_path: string;
  file_path: string | null;
  language: string | null;
  http_method: string | null;
  route_path: string | null;
  is_exported: boolean;
  is_async: boolean;
  start_line: number | null;
  end_line: number | null;
}

export interface RelatedNode extends ArchNodeSummary {
  edge_type: string | null;
}

export interface ComponentGroup {
  key: string;
  label: string;
  count: number;
  items: ArchNodeSummary[];
}

export interface ArchitectureComponents {
  repo_id: string;
  groups: ComponentGroup[];
}

export interface NodeDetails {
  node: ArchNodeSummary;
  file_path: string | null;
  signature: string | null;
  source_code: string | null;
  parent_class: ArchNodeSummary | null;
  callers: ArchNodeSummary[];
  callees: ArchNodeSummary[];
  services: ArchNodeSummary[];
  tables: RelatedNode[];
  dependencies: RelatedNode[];
  // Evidence tracking
  total_inbound_edges: number;
  total_outbound_edges: number;
  edge_types_found: string[];
}

export interface DependencyEdge {
  from_node_id: string;
  from_name: string;
  to_node_id: string;
  to_name: string;
  edge_type: string;
}

export interface ArchitectureDependencies {
  repo_id: string;
  total_edges: number;
  edge_type_counts: Record<string, number>;
  edges: DependencyEdge[];
}


export interface Hotspot {
  node_id: string;
  name: string;
  type: string;
  reason: string;
  score: number;
}

export interface ArchitectureHealthReport {
  overall_score: number;
  architecture_health: string;
  complexity_score: number;
  coupling_score: number;
  maintainability_score: number;
  risk_score: number;
  hotspots: Hotspot[];
  recommendations: string[];
}

export const architectureService = {
  getOverview: async (repoId: string): Promise<ArchitectureOverview> => {
    const res = await API.get(`/api/repos/${repoId}/architecture/overview`);
    return res.data;
  },
  getComponents: async (repoId: string): Promise<ArchitectureComponents> => {
    const res = await API.get(`/api/repos/${repoId}/architecture/components`);
    return res.data;
  },
  getNode: async (repoId: string, nodeId: string): Promise<NodeDetails> => {
    const res = await API.get(`/api/repos/${repoId}/architecture/node/${nodeId}`);
    return res.data;
  },
  getDependencies: async (repoId: string): Promise<ArchitectureDependencies> => {
    const res = await API.get(`/api/repos/${repoId}/architecture/dependencies`);
    return res.data;
  },

  getHealth: async (repoId: string): Promise<ArchitectureHealthReport> => {
    const res = await API.get(`/api/repos/${repoId}/architecture/health`);
    return res.data;
  },
};
