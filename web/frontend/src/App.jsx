import { useState, useEffect } from 'react'
import ConvertPage from './features/convert/ConvertPage'
import SplitManager from './SplitManager'
import LogViewer from './LogViewer'

function getRouteFromHash() {
  const hash = window.location.hash.replace('#/', '') || 'convert'
  return hash
}

export default function App() {
  const [view, setView] = useState(getRouteFromHash)

  useEffect(() => {
    const handler = () => setView(getRouteFromHash())
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [])

  if (view === 'split') {
    return <SplitManager onBack={() => { window.location.hash = '/convert' }} />
  }

  if (view === 'log') {
    return <LogViewer onBack={() => { window.location.hash = '/convert' }} />
  }

  return <ConvertPage
    onOpenSplit={() => { window.location.hash = '/split' }}
  />
}
