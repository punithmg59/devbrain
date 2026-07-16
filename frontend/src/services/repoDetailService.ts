/**
 * Repo-detail API service — file tree, files, nodes, stats, Groq summaries.
 * Uses the same axios instance as authService (withCredentials: true).
 */

import API from "./authService";
import type {
  ApiRoutes,
  FileDetail,
  FileTreeNode,
  NodeSummary,
  PaginatedFiles,
  PaginatedNodes,
  RepoDetail,
  RepoStats,
} from "../types/repo";

// ── Repo detail ────────────────────────────────────────────────

export async function getRepoDetail(repoId: string): Promise<RepoDetail> {
  try {
    const res = await API.get(`/api/repos/${repoId}`);
    return res.data;
  } catch (err: any) {
    throw new Error(err.response?.data?.detail ?? "Failed to load repository details");
  }
}

// ── File tree ──────────────────────────────────────────────────

export async function getFileTree(repoId: string): Promise<FileTreeNode[]> {
  try {
    const res = await API.get(`/api/repos/${repoId}/tree`);
    return res.data;
  } catch (err: any) {
    throw new Error(err.response?.data?.detail ?? "Failed to load file tree");
  }
}

// ── Files ──────────────────────────────────────────────────────

export async function getFiles(
  repoId: string,
  params?: {
    folder_path?: string;
    extension?: string;
    page?: number;
    limit?: number;
  }
): Promise<PaginatedFiles> {
  try {
    const res = await API.get(`/api/repos/${repoId}/files`, { params });
    return res.data;
  } catch (err: any) {
    throw new Error(err.response?.data?.detail ?? "Failed to load files");
  }
}

export async function getFile(repoId: string, fileId: string): Promise<FileDetail> {
  try {
    const res = await API.get(`/api/repos/${repoId}/files/${fileId}`);
    return res.data;
  } catch (err: any) {
    throw new Error(err.response?.data?.detail ?? "Failed to load file");
  }
}

// ── Nodes ──────────────────────────────────────────────────────

export async function getNodes(
  repoId: string,
  params?: {
    node_type?: string;
    search?: string;
    file_path?: string;
    page?: number;
    limit?: number;
  }
): Promise<PaginatedNodes> {
  try {
    const res = await API.get(`/api/repos/${repoId}/nodes`, { params });
    return res.data;
  } catch (err: any) {
    throw new Error(err.response?.data?.detail ?? "Failed to load nodes");
  }
}



export async function getNodeDependencies(repoId: string, nodeId: string): Promise<import("../types/repo").NodeDependenciesResponse> {
  try {
    const res = await API.get(`/api/repos/${repoId}/nodes/${nodeId}/dependencies`);
    return res.data;
  } catch (err: any) {
    throw new Error(err.response?.data?.detail ?? "Failed to load node dependencies");
  }
}

// ── Stats ──────────────────────────────────────────────────────

export async function getRepoStats(repoId: string): Promise<RepoStats> {
  try {
    const res = await API.get(`/api/repos/${repoId}/stats`);
    return res.data;
  } catch (err: any) {
    throw new Error(err.response?.data?.detail ?? "Failed to load stats");
  }
}

// ── API Routes ─────────────────────────────────────────────────

export async function getApiRoutes(repoId: string): Promise<ApiRoutes> {
  try {
    const res = await API.get(`/api/repos/${repoId}/api-routes`);
    return res.data;
  } catch (err: any) {
    throw new Error(err.response?.data?.detail ?? "Failed to load API routes");
  }
}

// ── Groq summaries ─────────────────────────────────────────────

export async function summarizeNode(
  repoId: string,
  nodeId: string,
  force?: boolean
): Promise<NodeSummary> {
  try {
    const res = await API.post(
      `/api/repos/${repoId}/nodes/${nodeId}/summarize`,
      { force: force || false }
    );
    return res.data;
  } catch (err: any) {
    throw new Error(err.response?.data?.detail ?? "Failed to summarize node");
  }
}

