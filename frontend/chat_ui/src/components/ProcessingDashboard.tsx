import React, { useEffect, useState } from 'react'
import { getAllStatus, runProcess, reprocess, PipelineStatusItem } from '../lib/pipelineApi'

export default function ProcessingDashboard() {
  const [items, setItems] = useState<PipelineStatusItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stages, setStages] = useState<{asr:boolean; validate:boolean; embed:boolean}>({asr:true, validate:true, embed:true})
  const [resume, setResume] = useState(true)
  const [overwrite, setOverwrite] = useState(false)

  async function refresh() {
    try {
      setError(null)
      const data = await getAllStatus()
      setItems(data)
    } catch (e:any) {
      setError(e.message)
    }
  }

  useEffect(() => {
    refresh()
    const t = setInterval(refresh, 8000)
    return () => clearInterval(t)
  }, [])

  async function onRunPipeline() {
    setLoading(true)
    try {
      await runProcess({
        stages: [stages.asr && 'asr', stages.validate && 'validate', stages.embed && 'embed'].filter(Boolean) as any,
        resume,
        overwrite_existing: overwrite,
        scope: 'all'
      })
      await refresh()
    } catch (e:any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const badge = (ok?: boolean, err?: string | null) => {
    if (err) return <span style={{color:'#b91c1c'}}>❌</span>
    if (ok) return <span style={{color:'#0f766e'}}>✅</span>
    return <span style={{color:'#ca8a04'}}>⏳</span>
  }

  return (
    <div style={{display:'flex', height:'100%', gap:16}}>
      <div style={{flex:1, padding:16, overflow:'auto'}}>
        <h2 style={{margin:'8px 0'}}>Processing Dashboard</h2>
        {error && <div style={{color:'#b91c1c', marginBottom:8}}>Error: {error}</div>}
        <div style={{display:'flex', gap:12, marginBottom:12}}>
          <label><input type="checkbox" checked={stages.asr} onChange={e=>setStages(s=>({...s, asr: e.target.checked}))}/> ASR GPU</label>
          <label><input type="checkbox" checked={stages.validate} onChange={e=>setStages(s=>({...s, validate: e.target.checked}))}/> Validation</label>
          <label><input type="checkbox" checked={stages.embed} onChange={e=>setStages(s=>({...s, embed: e.target.checked}))}/> Embeddings</label>
          <label><input type="checkbox" checked={resume} onChange={e=>setResume(e.target.checked)}/> Resume incomplete</label>
          <label><input type="checkbox" checked={overwrite} onChange={e=>setOverwrite(e.target.checked)}/> Overwrite existing</label>
          <button onClick={onRunPipeline} disabled={loading} style={{padding:'6px 10px', border:'1px solid #d1d5db', borderRadius:6}}>
            {loading ? 'Running…' : 'Run Pipeline'}
          </button>
        </div>
        <table style={{width:'100%', borderCollapse:'collapse'}}>
          <thead>
            <tr style={{textAlign:'left', borderBottom:'1px solid #e5e7eb'}}>
              <th style={{padding:8}}>File</th>
              <th style={{padding:8}}>Type</th>
              <th style={{padding:8}}>ASR</th>
              <th style={{padding:8}}>Validation</th>
              <th style={{padding:8}}>Embedding</th>
              <th style={{padding:8}}>Updated</th>
              <th style={{padding:8}}></th>
            </tr>
          </thead>
          <tbody>
            {items.map(it => (
              <tr key={it.file_id} style={{borderBottom:'1px solid #f3f4f6'}}>
                <td style={{padding:8}}>{it.filename}</td>
                <td style={{padding:8}}>{it.file_type}</td>
                <td style={{padding:8}}>{badge(it.asr_done, it.asr_error)}</td>
                <td style={{padding:8}}>{badge(it.validation_done, it.validation_error)}</td>
                <td style={{padding:8}}>{badge(it.embedding_done, it.embedding_error)}</td>
                <td style={{padding:8}}>{it.last_update ? new Date(it.last_update).toLocaleString() : ''}</td>
                <td style={{padding:8}}>
                  <button onClick={async()=>{ await reprocess(it.file_id, ['validate']); await refresh(); }} style={{padding:'4px 8px', border:'1px solid #d1d5db', borderRadius:6}}>Reprocess</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
