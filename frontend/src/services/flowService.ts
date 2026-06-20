import API from "./authService";

export interface FlowNodeRef {
  id: string;
  name: string;
  node_type: string;
  file_path?: string | null;
  http_method?: string | null;
  route_path?: string | null;
}

export interface FlowStep {
  order: number;
  depth: number;
  edge_type: string;
  from_node: FlowNodeRef;
  to_node: FlowNodeRef;
}

export interface Flow {
  flow_id: string;
  flow_name: string;
  flow_type: string;
  root_node: FlowNodeRef;
  steps: FlowStep[];
  critical_nodes: FlowNodeRef[];
  dependencies: FlowNodeRef[];
  node_count: number;
  edge_count: number;
  truncated: boolean;
}

export interface FlowSummary {
  flow_id: string;
  flow_name: string;
  flow_type: string;
  root_node: FlowNodeRef;
  step_count: number;
  critical_node_count: number;
}

export interface FlowTypeCount {
  flow_type: string;
  count: number;
}

export interface FlowListResponse {
  repo_id: string;
  total: number;
  type_counts: FlowTypeCount[];
  flows: FlowSummary[];
}

export interface FlowDetailResponse {
  repo_id: string;
  flow: Flow;
}

export interface FlowsFromNodeResponse {
  repo_id: string;
  node: FlowNodeRef;
  total: number;
  flows: Flow[];
}

export const flowService = {
  listFlows: async (repoId: string): Promise<FlowListResponse> => {
    const res = await API.get(`/api/repos/${repoId}/flows`);
    return res.data;
  },
  getFlow: async (repoId: string, flowId: string): Promise<FlowDetailResponse> => {
    const res = await API.get(`/api/repos/${repoId}/flows/${encodeURIComponent(flowId)}`);
    return res.data;
  },
  getFlowsFromNode: async (repoId: string, nodeId: string): Promise<FlowsFromNodeResponse> => {
    const res = await API.get(`/api/repos/${repoId}/flows/from-node/${nodeId}`);
    return res.data;
  },
};
