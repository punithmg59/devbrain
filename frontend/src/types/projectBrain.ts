export interface RepoIntelligenceScore {
  total_score: number;
  code_health: number;
  dependency_health: number;
  architecture_health: number;
  engineering_quality: number;
  risk_exposure: number;
}

export interface ArchitectureMap {
  frontend_components: number;
  backend_services: number;
  api_routes: number;
  database_tables: number;
}

export interface DependencyHealth {
  healthy: number;
  risky: number;
  circular: number;
  orphaned: number;
}

export interface CriticalFunction {
  node_id: string;
  name: string;
  file_path: string;
  importance_score: number;
  inbound_calls: number;
  api_usage: number;
  db_usage: number;
  service_usage: number;
}

export interface ConnectedComponent {
  node_id: string;
  name: string;
  degree: number;
}

export interface DatabaseHotspot {
  node_id: string;
  name: string;
  total_reads: number;
  total_writes: number;
  total_updates: number;
  total_deletes: number;
  touching_functions: string[];
}

export interface HighRiskApi {
  node_id: string;
  name: string;
  route_path: string | null;
  risk_score: number;
  tables_touched: number;
  functions_touched: number;
}

export interface ArchitectureViolation {
  id: string;
  severity: string; // Critical, High, Medium, Info
  rule_name: string;
  description: string;
  source_node_id: string | null;
  target_node_id: string | null;
  file_path: string | null;
}

export interface ProjectBrainResponse {
  repo_id: string;
  intelligence_score: RepoIntelligenceScore;
  architecture_map: ArchitectureMap;
  dependency_health: DependencyHealth;
  critical_functions: CriticalFunction[];
  connected_components: ConnectedComponent[];
  database_hotspots: DatabaseHotspot[];
  high_risk_apis: HighRiskApi[];
  architecture_violations: ArchitectureViolation[];
}
