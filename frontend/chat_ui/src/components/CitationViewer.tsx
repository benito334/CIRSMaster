import React from 'react'

type Props = {
  citations: { source_id?: string; start_time?: number; end_time?: number; chunk_id?: string }[]
}

export default function CitationViewer({ citations }: Props) {
  if (!citations?.length) return null
  return (
    <div style={{borderTop:'1px dashed #e5e7eb', paddingTop:8, marginTop:8}}>
      <strong style={{fontSize:12}}>Citations</strong>
      <ul style={{fontSize:12, color:'#374151', marginTop:6}}>
        {citations.map((c,i)=> (
          <li key={i}>
            [{c.source_id || 'src'}] t={c.start_time}-{c.end_time} (chunk {c.chunk_id})
          </li>
        ))}
      </ul>
    </div>
  )
}
