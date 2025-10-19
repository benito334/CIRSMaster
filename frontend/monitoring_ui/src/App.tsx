import React, { useEffect, useState } from 'react'
import axios from 'axios'

const MON_URL = (import.meta as any).env?.VITE_MONITOR_URL || 'http://localhost:8010'

function MetricCards({ data }: { data: any }) {
  return (
    <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:12}}>
      <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
        <div style={{fontSize:12, color:'#6b7280'}}>Retrieval Confidence (avg)</div>
        <div style={{fontSize:24}}>{data?.retrieval_confidence_avg ?? '—'}</div>
      </div>
      <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
        <div style={{fontSize:12, color:'#6b7280'}}>LLM Latency (ms)</div>
        <div style={{fontSize:24}}>{data?.llm_latency_ms ?? '—'}</div>
      </div>
      <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
        <div style={{fontSize:12, color:'#6b7280'}}>GPU Util (%)</div>
        <div style={{fontSize:24}}>{data?.gpu_utilization_percent ?? '—'}</div>
      </div>
    </div>
  )
}

function ProvenanceGraph({ items }: { items: any[] }) {
  return (
    <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12, minHeight:200}}>
      <strong>Provenance (chunks → sources)</strong>
      <ul style={{fontSize:12}}>
        {items.map((r,i)=> (
          <li key={i}>[{r.source_id}] {r.start_time}-{r.end_time} — {String(r.text).slice(0,90)}...</li>
        ))}
      </ul>
    </div>
  )
}

export default function App(){
  const [metrics, setMetrics] = useState<any>({})
  const [prov, setProv] = useState<any>({retrieved_chunks: []})

  async function fetchMetrics(){
    try {
      const resp = await fetch(`${MON_URL}/metrics`)
      const txt = await resp.text()
      // Tiny scrape to demo
      const rc = /retrieval_confidence_avg\s+(\d+\.?\d*)/.exec(txt)?.[1]
      setMetrics({ retrieval_confidence_avg: rc })
    } catch {}
  }

  async function fetchProv(){
    try {
      const { data } = await axios.post(`${MON_URL}/provenance/demo`, { retrieved: [] })
      setProv(data)
    } catch {}
  }

  useEffect(()=>{
    fetchMetrics(); fetchProv()
    const id = setInterval(fetchMetrics, 10000)
    return ()=>clearInterval(id)
  }, [])

  return (
    <div style={{fontFamily:'Inter, system-ui, Arial', padding:16, display:'grid', gap:16}}>
      <header style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
        <strong>Monitoring Dashboard</strong>
        <div style={{fontSize:12, color:'#6b7280'}}>Source: {MON_URL}</div>
      </header>
      <MetricCards data={metrics} />
      <ProvenanceGraph items={prov.retrieved_chunks||[]} />
    </div>
  )
}
