export interface CallerNode {
  id: string
  name: string
  type: string
  file: string
  depth: number
  critical: boolean
  start_line?: number
  end_line?: number
}

export interface CallersSummary {
  total_callers: number
  critical_callers: number
  api_routes: number
  services: number
  classes: number
  functions: number
  workflows: number
}

export interface CallersTarget {
  id: string
  name: string
  type: string
}

export interface CallersResponse {
  target: CallersTarget
  summary: CallersSummary
  callers: CallerNode[]
}

export type CallerFilter = 'all' | 'api_route' | 'service' | 'class' | 'function' | 'workflow'
