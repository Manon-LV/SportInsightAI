import type {
  EventPrediction,
  InferenceRequest,
  InferenceResponse,
  VideoAvailabilityResponse,
  ClipRequest,
  SoccerNetDownloadRequest,
  SoccerNetDownloadStatus,
  MatchSummary,
  SplitSummary,
  SplitIntegrityResponse
} from '../types/predictions'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `HTTP ${response.status}`)
  }

  return response.json() as Promise<T>
}

export function runInference(payload: InferenceRequest): Promise<InferenceResponse> {
  return requestJson<InferenceResponse>('/inference/run', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function getHealth(): Promise<{ status: string; service: string }> {
  return requestJson('/health')
}

export async function loadDemoPredictions(): Promise<EventPrediction[]> {
  const response = await fetch('/demo_predictions_clean.json')
  if (!response.ok) {
    throw new Error('Impossible de charger public/demo_predictions_clean.json')
  }
  return response.json() as Promise<EventPrediction[]>
}

export function getSplits(splitsDir = 'splits'): Promise<SplitSummary[]> {
  return requestJson<SplitSummary[]>(`/splits?splits_dir=${encodeURIComponent(splitsDir)}`)
}

export function getSplitIntegrity(splitsDir = 'splits'): Promise<SplitIntegrityResponse> {
  return requestJson<SplitIntegrityResponse>(`/splits/integrity?splits_dir=${encodeURIComponent(splitsDir)}`)
}

export function getSplitMatches(splitName = 'test', root = 'data/SoccerNet', splitsDir = 'splits', limit = 200): Promise<MatchSummary[]> {
  const params = new URLSearchParams()
  params.set('root', root)
  params.set('splits_dir', splitsDir)
  params.set('limit', String(limit))
  return requestJson<MatchSummary[]>(`/splits/${encodeURIComponent(splitName)}/matches?${params.toString()}`)
}

export function getVideoAvailability(matchDir: string): Promise<VideoAvailabilityResponse> {
  return requestJson<VideoAvailabilityResponse>(`/media/video/availability?match_dir=${encodeURIComponent(matchDir)}`)
}

export function buildVideoUrl(matchDir: string, half: number, startSec?: number, endSec?: number): string {
  const base = `${API_BASE_URL}/media/video?match_dir=${encodeURIComponent(matchDir)}&half=${half}`
  if (typeof startSec === 'number' && typeof endSec === 'number') {
    return `${base}#t=${Math.max(0, startSec).toFixed(1)},${Math.max(startSec, endSec).toFixed(1)}`
  }
  return base
}

export function buildClipUrl(payload: ClipRequest): string {
  const params = new URLSearchParams()
  params.set('match_dir', payload.match_dir)
  params.set('half', String(payload.half))
  params.set('timestamp', String(payload.timestamp))
  params.set('before_sec', String(payload.before_sec))
  params.set('after_sec', String(payload.after_sec))
  return `${API_BASE_URL}/media/clip?${params.toString()}`
}

export function startSoccerNetVideoDownload(payload: SoccerNetDownloadRequest): Promise<SoccerNetDownloadStatus> {
  return requestJson<SoccerNetDownloadStatus>('/download/soccernet/videos', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function getSoccerNetDownloadStatus(jobId: string): Promise<SoccerNetDownloadStatus> {
  return requestJson<SoccerNetDownloadStatus>(`/download/soccernet/status/${encodeURIComponent(jobId)}`)
}
