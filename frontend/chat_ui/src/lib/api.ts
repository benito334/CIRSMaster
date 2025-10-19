import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8003'

export type ChatRequest = { query: string; mode?: 'vector'|'lexical'|'hybrid' }
export type ChatResponse = {
  answer: string
  citations: { source_id?: string; start_time?: number; end_time?: number; chunk_id?: string }[]
  confidence?: number | null
  mode: string
}

export async function chat(req: ChatRequest): Promise<ChatResponse> {
  const { data } = await axios.post(`${API_URL}/chat`, req)
  return data
}

export type ModuleRequest = { topic: string; mode?: 'vector'|'lexical'|'hybrid'; top_k?: number }
export async function buildModule(req: ModuleRequest): Promise<any> {
  const { data } = await axios.post(`${API_URL}/module`, req)
  return data
}
