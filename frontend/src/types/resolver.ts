export interface SmartResolvedEntity {
  entity_id: string
  entity_type: string
  name: string
  confidence: number
  reason: string
  source: string
  file_path?: string | null
  http_method?: string | null
  route_path?: string | null
  workflow_name?: string | null
  graph_connections: string[]
}

export interface ResolveResponse {
  query: string
  resolved_entities: SmartResolvedEntity[]
  primary_entity: SmartResolvedEntity | null
  resolution_ms: number
}

export interface AutocompleteSuggestion {
  label: string
  entity_type: string
  entity_id?: string | null
  file_path?: string | null
  source: string
  subtitle?: string | null
}

export interface AutocompleteResponse {
  suggestions: AutocompleteSuggestion[]
}
