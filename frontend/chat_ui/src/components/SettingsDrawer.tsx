import React, { useState } from 'react'

export default function SettingsDrawer() {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button onClick={()=>setOpen(o=>!o)} style={{padding:'6px 10px', border:'1px solid #d1d5db', borderRadius:6}}>Settings</button>
      {open && (
        <div style={{position:'absolute', right:16, top:56, background:'white', border:'1px solid #e5e7eb', borderRadius:8, padding:12, width:300, boxShadow:'0 10px 30px rgba(0,0,0,0.1)'}}>
          <div style={{fontSize:12, color:'#6b7280'}}>These settings reflect backend .env. Modify backend services to change defaults.</div>
          <ul style={{marginTop:8, fontSize:14, lineHeight:1.6}}>
            <li><strong>API URL</strong>: {import.meta.env.VITE_API_URL || 'http://localhost:8003'}</li>
            <li><strong>Default Mode</strong>: {import.meta.env.VITE_DEFAULT_MODE || 'hybrid'}</li>
            <li><strong>Max Tokens</strong>: {import.meta.env.VITE_MAX_TOKENS || 1500}</li>
            <li><strong>Temperature</strong>: {import.meta.env.VITE_TEMPERATURE || 0.3}</li>
          </ul>
        </div>
      )}
    </div>
  )
}
