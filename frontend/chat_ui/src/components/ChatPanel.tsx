import React, { useEffect, useMemo, useRef, useState } from 'react'
import { chat, ChatResponse } from '../lib/api'
import MessageBubble from './MessageBubble'

export default function ChatPanel() {
  const [messages, setMessages] = useState<Array<{role:'user'|'assistant', content:string, citations?: any[]}>>([])
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<'vector'|'lexical'|'hybrid'>(
    (import.meta.env.VITE_DEFAULT_MODE as any) || 'hybrid'
  )
  const [loading, setLoading] = useState(false)
  const scrollerRef = useRef<HTMLDivElement>(null)

  useEffect(()=>{
    scrollerRef.current?.scrollTo({top: scrollerRef.current.scrollHeight, behavior:'smooth'})
  }, [messages])

  async function send() {
    const q = input.trim()
    if (!q) return
    setInput('')
    setMessages(prev=>[...prev, {role:'user', content:q}])
    setLoading(true)
    try {
      const res: ChatResponse = await chat({ query: q, mode })
      setMessages(prev=>[...prev, {role:'assistant', content: res.answer || '', citations: res.citations || []}])
    } catch (e:any) {
      setMessages(prev=>[...prev, {role:'assistant', content: 'Error: ' + (e?.message||'request failed')}])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{display:'grid', gridTemplateRows:'1fr auto', height:'100%'}}>
      <div ref={scrollerRef} style={{overflowY:'auto', padding:16, display:'flex', flexDirection:'column', gap:12}}>
        {messages.map((m, idx)=> (
          <MessageBubble key={idx} role={m.role} content={m.content} citations={m.citations} />
        ))}
        {loading && <div style={{fontSize:12, color:'#6b7280'}}>Thinking…</div>}
      </div>
      <div style={{padding:12, borderTop:'1px solid #e5e7eb', display:'flex', gap:8, alignItems:'center'}}>
        <select value={mode} onChange={e=>setMode(e.target.value as any)} style={{border:'1px solid #d1d5db', borderRadius:6, padding:'6px'}}>
          <option value="hybrid">hybrid</option>
          <option value="vector">vector</option>
          <option value="lexical">lexical</option>
        </select>
        <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter') send() }}
               placeholder="Ask about CIRS…" style={{flex:1, border:'1px solid #d1d5db', borderRadius:6, padding:'10px'}} />
        <button onClick={send} disabled={loading} style={{padding:'10px 14px', borderRadius:6, background:'#111827', color:'white'}}>Send</button>
      </div>
    </div>
  )
}
