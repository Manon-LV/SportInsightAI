import type {
  EventPrediction,
  InferenceRequest,
  InferenceResponse,
  VideoAvailabilityResponse,
  ClipRequest,
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

// ============================================================================
// Upload et Features API
// ============================================================================

export interface UploadJobInfo {
  job_id: string
  message: string
}

export interface UploadStatus {
  job_id: string
  status: string
  match_name: string
  half_1_path: string | null
  half_2_path: string | null
  half_1_size: number
  half_2_size: number
  features_status: string
  match_dir: string | null
  message: string
  error: string | null
}

export interface CheckpointInfo {
  id: string
  path: string
  name: string
}

export async function createUploadJob(matchName: string): Promise<UploadJobInfo> {
  const formData = new FormData()
  formData.append('match_name', matchName)

  const response = await fetch(`${API_BASE_URL}/upload/create`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `HTTP ${response.status}`)
  }

  return response.json() as Promise<UploadJobInfo>
}

export async function uploadVideo(jobId: string, half: number, file: File): Promise<void> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/upload/${jobId}/video/${half}`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `HTTP ${response.status}`)
  }
}

export async function finalizeUpload(jobId: string): Promise<UploadStatus> {
  const response = await fetch(`${API_BASE_URL}/upload/${jobId}/finalize`, {
    method: 'POST'
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `HTTP ${response.status}`)
  }

  return response.json() as Promise<UploadStatus>
}

export async function extractFeatures(jobId: string, fps: number = 2.0, device: string = 'auto'): Promise<void> {
  const params = new URLSearchParams()
  params.set('fps', String(fps))
  params.set('device', device)

  const response = await fetch(`${API_BASE_URL}/upload/${jobId}/extract-features?${params.toString()}`, {
    method: 'POST'
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `HTTP ${response.status}`)
  }
}

export async function getUploadStatus(jobId: string): Promise<UploadStatus> {
  return requestJson<UploadStatus>(`/upload/${jobId}`)
}

export async function listCheckpoints(): Promise<CheckpointInfo[]> {
  return requestJson<CheckpointInfo[]>('/checkpoints')
}

export async function deleteUploadJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/upload/${jobId}`, {
    method: 'DELETE'
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `HTTP ${response.status}`)
  }
}

export async function uploadFeaturesFile(jobId: string, half: number, file: File): Promise<UploadStatus> {
  const formData = new FormData()
  formData.append('half', String(half))
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/upload/${jobId}/upload-features`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `HTTP ${response.status}`)
  }

  return response.json() as Promise<UploadStatus>
}

export async function importFeatures(jobId: string, files: Record<string, string>): Promise<any> {
  const formData = new FormData()
  formData.append('files', JSON.stringify(files))

  const response = await fetch(`${API_BASE_URL}/upload/${jobId}/import-features`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `HTTP ${response.status}`)
  }

  return response.json()
}

