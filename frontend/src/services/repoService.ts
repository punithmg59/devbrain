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

  analyze: async (repoId: string): Promise<{ repo_id: string; status: string; message: string }> => {
    const res = await API.post(`/api/repos/${repoId}/analyze`);
    return res.data;
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
};
