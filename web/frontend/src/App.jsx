import { useState } from 'react'
import ConvertPage from './features/convert/ConvertPage'
import SplitManager from './SplitManager'

export default function App() {
  const [view, setView] = useState('convert')

  if (view === 'split') {
    return <SplitManager onBack={() => setView('convert')} />
  }

  return <ConvertPage onOpenSplit={() => setView('split')} />
}
