export type HalfSelection = 'first' | 'second' | 'both'

export interface EventPrediction {
  half: number
  timestamp: number
  gameTime: string
  label: string
  score: number
}

export interface VideoHalfInfo {
  available: boolean
  name: string | null
  path: string | null
  media_type: string | null
}

export interface VideoAvailabilityResponse {
  match_dir: string
  halves: Record<string, VideoHalfInfo>
}

export interface ClipRequest {
  match_dir: string
  half: number
  timestamp: number
  before_sec: number
  after_sec: number
}

export interface MatchSummary {
  id: string
  path: string
  name: string
  has_first_half: boolean
  has_second_half: boolean
  split: string | null
}

export interface SplitSummary {
  name: string
  path: string
  exists: boolean
  count: number
}

export interface SplitIntegrityResponse {
  counts: Record<string, number>
  overlap_count: number
  overlaps: Array<Record<string, unknown>>
  is_disjoint: boolean
}

export interface RunSummary {
  run_id: string
  match_dir: string
  checkpoint: string
  half: string
  event_count: number
  counts_by_class: Record<string, number>
  counts_by_half: Record<string, number>
}

export interface InferenceRequest {
  match_dir: string
  checkpoint: string
  half: HalfSelection
  score_threshold: number
  nms_radius_sec: number
  selected_classes: string[]
  device: string
}

export interface InferenceResponse {
  run_id: string
  events: EventPrediction[]
  summary: RunSummary
}

export const PRODUCT_CLASSES = [
  'Goal',
  'Corner',
  'Yellow card',
  'Red card',
  'Penalty',
  'Substitution',
  'Offside',
  'Foul',
  'Shots on target',
  'Shots off target',
]
