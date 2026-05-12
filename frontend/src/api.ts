import type { BionicSettings } from './apiTypes'
import type { Document, Settings } from './types'

const API_BASE: string =
  (import.meta as unknown as { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE ??
  ''

export async function parseFile(file: File): Promise<Document> {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${API_BASE}/api/parse`, { method: 'POST', body: fd })
  if (!res.ok) {
    const detail = await safeDetail(res)
    throw new Error(detail ?? `Parse failed (${res.status})`)
  }
  return (await res.json()) as Document
}

export async function exportDocument(
  document: Document,
  settings: Settings,
  format: 'html' | 'docx' | 'txt',
  title?: string,
): Promise<Blob> {
  const payload = {
    document,
    settings: settingsToBackend(settings),
    format,
    title: title ?? null,
  }
  const res = await fetch(`${API_BASE}/api/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const detail = await safeDetail(res)
    throw new Error(detail ?? `Export failed (${res.status})`)
  }
  return await res.blob()
}

export function settingsToBackend(s: Settings): BionicSettings {
  return {
    enabled: s.bionicEnabled,
    fixation_ratio: s.fixationRatio,
    min_word_length: s.minWordLength,
    skip_short_words: s.skipShortWords,
    use_color_instead_of_bold: s.useColorInsteadOfBold,
    prefix_color: s.prefixColor,
    color_vowels: s.colorVowels,
    vowel_color: s.vowelColor,
    saccade_adaptive: s.saccadeAdaptive,
    eye_anchor: s.eyeAnchor,
    eye_anchor_color: s.eyeAnchorColor,
    phrase_chunking: s.phraseChunking,
    phrase_chunk_size: s.phraseChunkSize,
    pos_coloring: s.posColoring,
    pos_color: s.posColor,
  }
}

/**
 * Apply bionic transformation directly on the user's original file bytes.
 *
 * Preserves images, tables, charts, embedded objects, formulas (XLSX),
 * animations (PPTX), fonts, colors, headers/footers, and the document's
 * overall structure. The output file's format always matches the source
 * format.
 */
export async function exportDocumentInplace(
  file: File,
  settings: Settings,
): Promise<Blob> {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('settings', JSON.stringify(settingsToBackend(settings)))
  const res = await fetch(`${API_BASE}/api/export-inplace`, {
    method: 'POST',
    body: fd,
  })
  if (!res.ok) {
    const detail = await safeDetail(res)
    throw new Error(detail ?? `In-place export failed (${res.status})`)
  }
  return await res.blob()
}

export const INPLACE_FORMATS = new Set(['pdf', 'docx', 'pptx', 'xlsx'])

export function getExtension(filename: string): string {
  const i = filename.lastIndexOf('.')
  return i === -1 ? '' : filename.slice(i + 1).toLowerCase()
}

async function safeDetail(res: Response): Promise<string | null> {
  try {
    const j = await res.json()
    return typeof j?.detail === 'string' ? j.detail : null
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Guided-mode v2 calibration
// ---------------------------------------------------------------------------
export interface ASRSResponse {
  question_id: number
  value: number
}

export interface PVTResult {
  mean_rt_ms: number | null
  median_rt_ms: number | null
  lapses: number
  false_starts: number
  trials: number
}

export interface ReadingTestResult {
  words: number
  elapsed_ms: number
  self_reported_difficulty: number | null
}

export interface CalibrationRequestBody {
  asrs: ASRSResponse[]
  pvt: PVTResult | null
  reading: ReadingTestResult | null
}

export interface CalibrationResponse {
  profile: 'apaise' | 'equilibre' | 'concentre' | 'sprint'
  affinities: { apaise: number; equilibre: number; concentre: number; sprint: number }
  dimensions: {
    inattention: number
    hyperactivity_impulsivity: number
    working_memory: number
    processing_speed: number
    distraction_sensitivity: number
  }
  rationale: string
  confidence: number
  asrs_positive: boolean
  reading_wpm: number | null
}

export async function calibrateProfile(body: CalibrationRequestBody): Promise<CalibrationResponse> {
  const res = await fetch(`${API_BASE}/api/profile/calibrate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await safeDetail(res)
    throw new Error(detail ?? `Calibration failed (${res.status})`)
  }
  return (await res.json()) as CalibrationResponse
}

// ---------------------------------------------------------------------------
// Intention Studio (quantum-entropy wave emitter / receiver)
// ---------------------------------------------------------------------------
export interface WaveSignal {
  archetype: { code: string; name: string; tone: string; reflection: string }
  message: string
  signature: string
  source: 'anu_qrng' | 'os_csprng'
  used_llm: boolean
  timestamp: number
}

export async function emitWave(intention: string): Promise<WaveSignal> {
  const res = await fetch(`${API_BASE}/api/wave/emit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ intention }),
  })
  if (!res.ok) {
    const detail = await safeDetail(res)
    throw new Error(detail ?? `Émission échouée (${res.status})`)
  }
  return (await res.json()) as WaveSignal
}

export async function receiveWave(question: string): Promise<WaveSignal> {
  const res = await fetch(`${API_BASE}/api/wave/receive`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) {
    const detail = await safeDetail(res)
    throw new Error(detail ?? `Réception échouée (${res.status})`)
  }
  return (await res.json()) as WaveSignal
}
