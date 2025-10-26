import React, { useMemo, useState } from 'react'
import ChatPanel from './components/ChatPanel'
import ModuleBuilder from './components/ModuleBuilder'
import SettingsDrawer from './components/SettingsDrawer'
<<<<<<< HEAD
import ProcessingDashboard from './components/ProcessingDashboard'

export default function App() {
  const [tab, setTab] = useState<'chat' | 'learn' | 'processing'>('chat')
=======

export default function App() {
  const [tab, setTab] = useState<'chat' | 'learn'>('chat')
>>>>>>> origin/codex/review-repository-for-issues-and-updates

  return (
    <div style={{fontFamily:'Inter, system-ui, Arial', height:'100vh', display:'flex', flexDirection:'column'}}>
      <header style={{display:'flex', alignItems:'center', justifyContent:'space-between', padding:'10px 16px', borderBottom:'1px solid #e5e7eb'}}>
        <div style={{display:'flex', gap:12, alignItems:'center'}}>
          <strong>CIRS Agent</strong>
          <nav style={{display:'flex', gap:8}}>
            <button onClick={()=>setTab('chat')} style={{padding:'6px 10px', borderRadius:6, border:'1px solid #d1d5db', background: tab==='chat'? '#111827' : 'white', color: tab==='chat' ? 'white' : '#111827'}}>Chat</button>
            <button onClick={()=>setTab('learn')} style={{padding:'6px 10px', borderRadius:6, border:'1px solid #d1d5db', background: tab==='learn'? '#111827' : 'white', color: tab==='learn' ? 'white' : '#111827'}}>Learning Mode</button>
<<<<<<< HEAD
            <button onClick={()=>setTab('processing')} style={{padding:'6px 10px', borderRadius:6, border:'1px solid #d1d5db', background: tab==='processing'? '#111827' : 'white', color: tab==='processing' ? 'white' : '#111827'}}>Processing</button>
=======
>>>>>>> origin/codex/review-repository-for-issues-and-updates
          </nav>
        </div>
        <SettingsDrawer />
      </header>
      <main style={{flex:1, minHeight:0}}>
<<<<<<< HEAD
        {tab === 'chat' ? <ChatPanel /> : tab === 'learn' ? <ModuleBuilder /> : <ProcessingDashboard />}
=======
        {tab === 'chat' ? <ChatPanel /> : <ModuleBuilder />}
>>>>>>> origin/codex/review-repository-for-issues-and-updates
      </main>
    </div>
  )
}
