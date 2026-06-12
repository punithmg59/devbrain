import API from './authService'

export interface WorkflowSummary {
  id: string
  name: string
  description?: string | null
  criticality: string
  workflow_type: string
  confidence: number
  service_name?: string | null
  node_count: number
  api_count: number
}

export async function discoverWorkflows(repoId: string): Promise<{
  discovered: number
  workflows: WorkflowSummary[]
  message: string
}> {
  const res = await API.post(`/api/repos/${repoId}/workflows/discover`)
  return res.data
}

export async function listWorkflows(repoId: string): Promise<{
  workflows: WorkflowSummary[]
  total: number
}> {
  const res = await API.get(`/api/repos/${repoId}/workflows`)
  return res.data
}

export async function submitWorkflowFeedback(
  repoId: string,
  body: {
    query: string
    workflow_id: string
    accepted: boolean
    rejected: boolean
  }
): Promise<{ ok: boolean; workflow_id: string; new_confidence?: number; message: string }> {
  const res = await API.post(`/api/repos/${repoId}/workflows/feedback`, body)
  return res.data
}
