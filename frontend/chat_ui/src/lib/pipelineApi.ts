export const PIPELINE_API = (import.meta as any).env?.VITE_PIPELINE_API || 'http://localhost:8021'

export type PipelineStatusItem = {
  file_id: string
  filename: string
  file_type: string
  asr_done: boolean
  validation_done: boolean
  embedding_done: boolean
  asr_error?: string | null
  validation_error?: string | null
  embedding_error?: string | null
  last_update?: string
  run_tag?: string
}

export async function getAllStatus(): Promise<PipelineStatusItem[]> {
  const res = await fetch(`${PIPELINE_API}/status/all`)
  if (!res.ok) throw new Error(`status/all failed: ${res.status}`)
  const data = await res.json()
  return data.items || []
}

export async function runProcess(body: {
  stages: ('asr'|'validate'|'embed')[]
  overwrite_existing?: boolean
  resume?: boolean
  scope?: 'all' | 'source_type' | 'files'
  files?: string[]
}) {
  const res = await fetch(`${PIPELINE_API}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  if (!res.ok) throw new Error(`process failed: ${res.status}`)
  return res.json()
}

export async function reprocess(file_id: string, stages: ('asr'|'validate'|'embed')[]) {
  const res = await fetch(`${PIPELINE_API}/reprocess/${file_id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stages })
  })
  if (!res.ok) throw new Error(`reprocess failed: ${res.status}`)
  return res.json()
}
