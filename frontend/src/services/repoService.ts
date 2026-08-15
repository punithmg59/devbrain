import API from "./authService";

export interface ConnectedRepo {
  id: string;
  github_repo_id: number;
  full_name: string;
  name: string;
  description: string | null;
  default_branch: string;
  is_private: boolean;
  language: string | null;
  analysis_status: string;
  total_files: number;
  total_functions: number;
  total_lines: number;
  created_at: string;
}

export interface GitHubRepoItem {
  github_repo_id: number;
  full_name: string;
  name: string;
  description: string | null;
  default_branch: string;
  is_private: boolean;
  language: string | null;
  already_connected: boolean;
}

export interface AnalysisProgressResponse {
  status: string;
  current_stage: string;
  progress_percent: number;
  files_processed: number;
  files_total: number;
  functions_found: number;
  nodes_count: number;
  edges_count: number;
  files_failed: number;
  warnings: string[];
  duration_seconds: number | null;
  job_id: string | null;
}

export const repoService = {
  listConnected: async (): Promise<ConnectedRepo[]> => {
    const res = await API.get("/api/repos");
    return res.data;
  },

  listAvailable: async (): Promise<GitHubRepoItem[]> => {
    const res = await API.get("/api/repos/github/available");
    return res.data;
  },

  connect: async (githubRepoId: number): Promise<ConnectedRepo> => {
    const res = await API.post("/api/repos/connect", { github_repo_id: githubRepoId });
    return res.data;
  },

  disconnect: async (repoId: string): Promise<void> => {
    await API.delete(`/api/repos/${repoId}`);
  },

  analyze: async (repoId: string): Promise<{ repo_id: string; status: string; message: string; job_id?: string }> => {
    console.log(`[ANALYSIS_UI] starting_analysis POST /api/repos/${repoId}/analyze`);
    try {
      const res = await API.post(`/api/repos/${repoId}/analyze`);
      console.log(`[ANALYSIS_UI] analysis_response status=${res.status}`, res.data);
      return res.data;
    } catch (err) {
      console.error(`[ANALYSIS_UI] analysis_error repo_id=${repoId}:`, err);
      throw err;
    }
  },

  getAnalysisStatus: async (repoId: string): Promise<{
    repo_id: string;
    full_name: string;
    analysis_status: string;
    total_files: number;
    total_functions: number;
    total_lines: number;
    last_analyzed_at: string | null;
  }> => {
    const res = await API.get(`/api/repos/${repoId}/analysis`);
    return res.data;
  },

  getAnalysisProgress: async (repoId: string): Promise<AnalysisProgressResponse> => {
    const res = await API.get(`/api/repos/${repoId}/analysis-progress`);
    return res.data;
  },
};

