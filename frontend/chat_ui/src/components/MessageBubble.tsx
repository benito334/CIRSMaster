import React from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'

type Citation = { source_id?: string; start_time?: number; end_time?: number; chunk_id?: string }

type Props = {
  role: 'user'|'assistant'
  content: string
  citations?: Citation[]
}

export default function MessageBubble({ role, content, citations }: Props) {
  const bg = role === 'user' ? '#e5f0ff' : '#f3f4f6'
  return (
    <div style={{display:'flex', justifyContent: role==='user'?'flex-end':'flex-start'}}>
      <div style={{background:bg, border:'1px solid #e5e7eb', padding:12, borderRadius:10, maxWidth:720, whiteSpace:'pre-wrap'}}>
        <ReactMarkdown rehypePlugins={[rehypeHighlight]}>{content}</ReactMarkdown>
        {citations && citations.length>0 && (
          <div style={{marginTop:8, fontSize:12, color:'#6b7280'}}>
            Citations: {citations.map((c,i)=> (
              <span key={i} style={{marginRight:6}}>
                [{c.source_id || 'src'}@t={c.start_time}-{c.end_time}]
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )}
