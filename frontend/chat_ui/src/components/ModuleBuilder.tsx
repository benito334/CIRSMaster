import React, { useState } from 'react'
import { buildModule } from '../lib/api'

export default function ModuleBuilder() {
  const [topic, setTopic] = useState('CIRS basics')
  const [mode, setMode] = useState<'vector'|'lexical'|'hybrid'>(
    (import.meta.env.VITE_DEFAULT_MODE as any) || 'hybrid'
  )
  const [loading, setLoading] = useState(false)
  const [mod, setMod] = useState<any>(null)

  async function run() {
    setLoading(true)
    try {
      const data = await buildModule({ topic, mode, top_k: 8 })
      setMod(data)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{padding:16, display:'grid', gridTemplateRows:'auto 1fr', gap:16, height:'100%'}}>
      <div style={{display:'flex', gap:8}}>
        <input value={topic} onChange={e=>setTopic(e.target.value)} placeholder="Topic (e.g., Lyme co-infections)"
               style={{flex:1, border:'1px solid #d1d5db', borderRadius:6, padding:'10px'}}/>
        <select value={mode} onChange={e=>setMode(e.target.value as any)} style={{border:'1px solid #d1d5db', borderRadius:6, padding:'6px'}}>
          <option value="hybrid">hybrid</option>
          <option value="vector">vector</option>
          <option value="lexical">lexical</option>
        </select>
        <button onClick={run} disabled={loading} style={{padding:'10px 14px', borderRadius:6, background:'#111827', color:'white'}}>Build</button>
      </div>
      <div style={{overflowY:'auto'}}>
        {!mod && !loading && <div style={{color:'#6b7280'}}>Enter a topic and press Build.</div>}
        {loading && <div style={{color:'#6b7280'}}>Building…</div>}
        {mod && (
          <div style={{display:'grid', gap:16}}>
            <section>
              <h3>Objectives</h3>
              <ul>
                {(mod.objectives||[]).map((o:string, i:number)=> <li key={i}>{o}</li>)}
              </ul>
            </section>
            <section>
              <h3>Sections</h3>
              {(mod.sections||[]).map((s:any, i:number)=> (
                <div key={i} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
                  <strong>{s.title}</strong>
                  <p style={{whiteSpace:'pre-wrap'}}>{s.summary}</p>
                </div>
              ))}
            </section>
            <section>
              <h3>Quiz</h3>
              <ul>
                {(mod.quiz||[]).map((q:any, i:number)=> <li key={i}>{q.question}</li>)}
              </ul>
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
