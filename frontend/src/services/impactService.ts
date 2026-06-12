import type { AxiosRequestConfig } from 'axios'
import API from './authService'
import type { ImpactResult, ImpactRequest, ImpactSearchNode, ImpactGraphResponse, ImpactReportV2 } from '../types/impact'
import type {
  AutocompleteResponse,
  ResolveResponse,
} from '../types/resolver'

export const impactService = {
  async analyzeImpactV2(
    repoId: string,
    request: { query: string; scenario: string; new_name?: string; new_file_path?: string },
    config?: AxiosRequestConfig
  ): Promise<ImpactReportV2> {
    const res = await API.post(`/api/repos/${repoId}/impact-analysis`, request, config)
    return res.data
  },

  async analyzeImpact(
    repoId: string,
    request: ImpactRequest,
    config?: AxiosRequestConfig
  ): Promise<ImpactResult> {
    const res = await API.post(`/api/repos/${repoId}/impact`, request, config)
    return res.data
  },

  async searchNodes(
    repoId: string,
    query: string,
    config?: AxiosRequestConfig
  ): Promise<ImpactSearchNode[]> {
    const res = await API.get(`/api/repos/${repoId}/impact/search`, {
      ...config,
      params: { q: query },
    })
    return res.data.slice(0, 10)
  },

  async resolve(
    repoId: string,
    query: string,
    config?: AxiosRequestConfig
  ): Promise<ResolveResponse> {
    const res = await API.post(
      `/api/repos/${repoId}/impact/resolve`,
      { query, limit: 10 },
      config
    )
    return res.data
  },

  async autocomplete(
    repoId: string,
    q: string,
    config?: AxiosRequestConfig
  ): Promise<AutocompleteResponse> {
    const res = await API.get(`/api/repos/${repoId}/impact/autocomplete`, {
      ...config,
      params: { q },
    })
    return res.data
  },

  /**
   * Fetch exact dependency intelligence for a single node.
   * Returns L1 (direct), L2 (indirect), L3 (workflow) dependencies,
   * plus database/API/file dependency breakdowns.
   * Backed by a lightweight CTE graph traversal — does NOT invoke full analysis pipeline.
   */
  async getImpactGraph(
    repoId: string,
    nodeId: string,
    options: { maxDepth?: number; direction?: 'both' | 'downstream' | 'upstream' } = {},
    config?: AxiosRequestConfig
  ): Promise<ImpactGraphResponse> {
    const res = await API.get(`/api/repos/${repoId}/impact-graph/${nodeId}`, {
      ...config,
      params: {
        max_depth: options.maxDepth ?? 3,
        direction: options.direction ?? 'both',
      },
    })
    return res.data
  },
}
