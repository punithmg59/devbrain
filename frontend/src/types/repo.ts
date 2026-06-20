/** TypeScript types matching backend repo-detail schemas. */

/**
 * Statuses that mean analysis produced a usable graph. "completed_with_warnings"
 * means the graph was built but some files were skipped during parsing — it must
 * be treated as a success everywhere a completed repo would be (viewing graph,
 * impact, stats, re-analyze, etc.).
 */
export const ANALYZED_STATUSES = ["completed", "completed_with_warnings"] as const;

export function isAnalyzed(status?: string | null): boolean {
  return status === "completed" || status === "completed_with_warnings";
}

export interface FileTreeNode {
  id: string;
  name: string;
  path: string;
  type: "file" | "folder";
  depth: number;
  children: FileTreeNode[];
  file_count?: number;
  function_count?: number;
  extension?: string;
  language?: string;
  line_count?: number;
}

export interface FileResponse {
  id: string;
  repo_id: string;
  file_path: string;
  file_name: string;
  extension: string | null;
  language: string | null;
  folder_path: string;
  depth: number;
  size_bytes: number;
  line_count: number;
  content_preview: string | null;
  importance_score: number;
}

export interface NodeResponse {
  id: string;
  repo_id: string;
  file_id: string | null;
  node_type: string;
  name: string;
  full_path: string;
  start_line: number | null;
  end_line: number | null;
  raw_code: string | null;
  signature: string | null;
  calls: string[];
  called_by: string[];
  http_method: string | null;
  route_path: string | null;
  summary: string | null;
  detailed_explanation?: string | null;
  architecture_role?: string | null;
  complexity_level?: string | null;
  call_flow_diagram?: string | null;
  ai_tags?: string[];
  potential_risks?: string[];
  dependencies?: string[];
  responsibilities?: string[];
  inputs?: string[];
  outputs?: string[];
  related_components?: string[];
  call_flow?: string[];
  tags: string[];
  is_exported: boolean;
  is_async: boolean;
  complexity_score: number;
}

export interface EdgeResponse {
  id: string;
  from_node_id: string;
  to_node_id: string;
  edge_type: string;
  weight: number;
}

export interface RepoStats {
  node_types: Record<string, number>;
  extensions: Record<string, number>;
  languages: Record<string, number>;
  top_files_by_size: FileResponse[];
  top_complex_nodes: NodeResponse[];
  total_edges: number;
  total_api_routes: number;
}

export interface PaginatedFiles {
  files: FileResponse[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface PaginatedNodes {
  nodes: NodeResponse[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface FileDetail {
  file: FileResponse;
  nodes: NodeResponse[];
}

export interface NodeRelation {
  edge_id: string;
  node_id: string;
  name: string;
  type: string;
  full_path: string;
  file_path?: string;
  edge_type: string;
}

export interface DependencyRisk {
  score: number;
  level: "low" | "medium" | "high" | "critical";
  reason: string;
}

export interface NodeDependenciesResponse {
  node: NodeResponse;
  calls: NodeRelation[];
  called_by: NodeRelation[];
  api_routes: NodeRelation[];
  reads_tables: NodeRelation[];
  writes_tables: NodeRelation[];
  updates_tables: NodeRelation[];
  deletes_tables: NodeRelation[];
  services: NodeRelation[];
  auth_dependencies: NodeRelation[];
  imports: NodeRelation[];
  inherits: NodeRelation[];
  contains: NodeRelation[];
  dependency_injections: NodeRelation[];
  risk: DependencyRisk;
}
export interface ApiRoutes {
  routes: NodeResponse[];
  total: number;
}

export interface NodeSummary {
  node_id: string;
  summary: string;
  detailed_explanation?: string | null;
  architecture_role?: string | null;
  complexity_level?: string | null;
  call_flow_diagram?: string | null;
  ai_tags?: string[];
  potential_risks?: string[];
  dependencies?: string[];
  responsibilities?: string[];
  inputs?: string[];
  outputs?: string[];
  related_components?: string[];
  call_flow?: string[];
  tags: string[];
}

export interface BatchSummarize {
  message: string;
  nodes_to_process: number;
}

export interface RepoDetail {
  id: string;
  full_name: string;
  name: string;
  description: string | null;
  language: string | null;
  analysis_status: string;
  last_analyzed_at: string | null;
  total_files: number;
  total_functions: number;
  total_lines: number;
}
