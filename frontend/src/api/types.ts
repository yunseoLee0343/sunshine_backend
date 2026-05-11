// TypeScript interfaces derived from the Ticket-26 backend response contract.
// Field names match the backend JSON keys exactly.
//
// Section "Actual backend shapes" below uses field names from the real
// Pydantic schemas (app/schemas/plants.py) which differ slightly from the
// Ticket-26 contract doc — they are used by the onboarding API module.

// ---------------------------------------------------------------------------
// Actual backend shapes (onboarding flow)
// ---------------------------------------------------------------------------

export interface SpeciesCandidateItem {
  species_profile_id: string | null
  label_ko: string
  label_en: string
  scientific_name: string | null
  confidence: number
  confidence_label: 'high' | 'medium' | 'low'
  source: string
}

export interface SpeciesCandidatesResponse {
  candidates: SpeciesCandidateItem[]
}

export interface SpeciesBlock {
  korean_name: string
  scientific_name: string | null
  common_name: string | null
}

export interface CharacterBlock {
  mood: string
  expression: string
  status_message: string
  primary_action: string
  reason_code: string
}

export interface PlantCard {
  plant_id: string
  user_id: string
  species_profile_id: string | null
  nickname: string
  room_name: string | null
  species: SpeciesBlock | null
  character: CharacterBlock
}

export interface CreatePlantResponse {
  plant: PlantCard
}

// ---------------------------------------------------------------------------
// Home (GET /home, GET /plants/:id/card) — actual backend shapes
// ---------------------------------------------------------------------------

export type CareStatus = 'good' | 'needs_action' | 'watch' | 'insufficient_data'
export type PrimaryAction =
  | 'none'
  | 'water'
  | 'increase_light'
  | 'stabilize_humidity'
  | 'adjust_temperature'
  | 'watch'
  | 'move_to_brighter_place'

export interface CharacterSummary {
  mood: string
  expression: string
  status_message: string
  primary_action: string
  reason_code: string
}

export interface EnvironmentBlock {
  soil_moisture_avg_pct: number | null
  light_avg_lux: number | null
  humidity_avg_pct: number | null
  temperature_avg_c: number | null
}

export interface PlantHomeCard {
  plant_id: string
  nickname: string
  room_name: string | null
  species_name: string | null
  character: CharacterSummary
  environment: EnvironmentBlock | null
  today_recommended_action: PrimaryAction
  care_status: CareStatus
}

export interface HomeResponse {
  user_id: string
  plants: PlantHomeCard[]
}

export interface GetPlantResponse {
  plant: PlantCard
}

// ---------------------------------------------------------------------------
// Environment detail (GET /plants/:id/environment) — actual backend shapes
// ---------------------------------------------------------------------------

export interface EnvMetricStats {
  avg: number | null
  min: number | null
  max: number | null
}

export interface WindowSnapshot {
  window: string
  window_start: string
  window_end: string
  temperature_c: EnvMetricStats
  humidity_pct: EnvMetricStats
  light_lux: EnvMetricStats
  soil_moisture_pct: EnvMetricStats
}

export interface CharacterExplanation {
  reason_code: string
  explanation: string
}

export interface EnvironmentDetailResponse {
  plant_id: string
  nickname: string
  room_name: string | null
  latest: WindowSnapshot | null
  summary_24h: WindowSnapshot | null
  summary_7d: WindowSnapshot | null
  character_explanation: CharacterExplanation | null
}

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

export interface Pagination {
  limit: number
  offset: number
  total: number
  has_more: boolean
}

export interface CharacterState {
  mood: string
  expression: string
  status_message: string
  primary_action: string | null
  reason_code: string
}

export interface LatestEnvironment {
  temperature_c: number | null
  humidity_pct: number | null
  light_lux: number | null
  soil_moisture_pct: number | null
  measured_at: string
}

export interface TodayAction {
  action: string
  severity: 'info' | 'warning' | 'critical'
  reason: string
}

// ---------------------------------------------------------------------------
// Species / Onboarding
// ---------------------------------------------------------------------------

export interface SpeciesCandidate {
  species_id: string
  common_name_ko: string
  common_name_en: string
  confidence_label: 'high' | 'medium' | 'low'
}

export interface SpeciesCandidateResponse {
  request_id: string
  image_ref: string
  candidates: SpeciesCandidate[]
  fallback: string | null
}

export interface PlantCreatedResponse {
  plant_id: string
  user_id: string
  nickname: string
  species_id: string
  species_name: string
  room: string
  character: CharacterState
}

// ---------------------------------------------------------------------------
// Plant list / detail
// ---------------------------------------------------------------------------

export interface PlantSpeciesSummary {
  species_profile_id: string
  korean_name: string
  scientific_name: string
  common_name: string
}

export interface PlantSummary {
  plant_id: string
  nickname: string
  room_name: string
  species: PlantSpeciesSummary
  character: CharacterState
}

export interface PlantListResponse {
  plants: PlantSummary[]
  pagination: Pagination
}

// ---------------------------------------------------------------------------
// Home plant card
// ---------------------------------------------------------------------------

export interface HomePlantCard {
  plant_id: string
  nickname: string
  species_name: string
  room: string
  character: CharacterState
  latest_environment: LatestEnvironment | null
  today_action: TodayAction | null
}

// ---------------------------------------------------------------------------
// Care log
// ---------------------------------------------------------------------------

export interface CareLogFeedback {
  character_mood: string
  message: string
}

export interface CareLogFeedbackResponse {
  care_log_id: string
  plant_id: string
  action: string
  recorded_at: string
  feedback: CareLogFeedback
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export interface ChatAnswerSections {
  결론: string
  근거: string
  행동: string
  주의: string
}

export interface ChatAnswer {
  text: string
  sections: ChatAnswerSections
}

export interface ChatEvidence {
  prompt_hash: string
  provider: string
  model: string
  rule_result_ids: string[]
  retrieved_chunk_ids: string[]
}

export interface ChatAnswerResponse {
  request_id: string
  plant_id: string
  intent: string
  profile: string
  answer: ChatAnswer
  evidence: ChatEvidence
}

// ---------------------------------------------------------------------------
// Companion recommendation
// ---------------------------------------------------------------------------

export interface CompanionReasonDimension {
  dimension: string
  decision: 'compatible' | 'incompatible' | 'caution'
  message: string
}

export interface CompanionRecommendation {
  species_id: string
  common_name: string
  decision: 'compatible' | 'incompatible' | 'caution'
  score: number
  reasons: CompanionReasonDimension[]
  caution_notes: string[]
  source_chunk_ids: string[]
}

export interface CompanionEvidence {
  current_species_id: string
  snapshot_id: string
  candidate_count: number
  filter_version: string
}

export interface CompanionRecommendationResponse {
  plant_id: string
  room_id: string
  recommendations: CompanionRecommendation[]
  evidence: CompanionEvidence
}

// ---------------------------------------------------------------------------
// Growth history
// ---------------------------------------------------------------------------

export interface HistoryItem {
  type: 'care_log' | 'environment_summary' | 'character_state'
  timestamp: string
  title: string
  summary: string
}

export interface GrowthHistoryResponse {
  plant_id: string
  items: HistoryItem[]
}

// ---------------------------------------------------------------------------
// Error
// ---------------------------------------------------------------------------

export interface ApiError {
  code?: string
  message: string
  details?: Record<string, unknown>
}
