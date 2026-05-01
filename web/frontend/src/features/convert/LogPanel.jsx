import { useMemo } from 'react'

export default function LogPanel({ lines, onClear }) {
  const text = useMemo(() => lines.map(l => l.msg).join('\n'), [lines])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // ignore
    }
  }

  if (!lines?.length) return null

  return (
    <section className="convert-panel convert-log-panel">
      <div className="convert-panel__header">
        <span>处理日志</span>
        <div className="convert-panel__actions">
          <button className="convert-link-btn" type="button" onClick={handleCopy}>复制</button>
          <button className="convert-link-btn" type="button" onClick={onClear}>清除</button>
        </div>
      </div>
      <div className="convert-panel__body convert-log-body">
        {lines.map(l => (
          <div key={l.id} className={`convert-log-line log-${l.type}`}>{l.msg}</div>
        ))}
      </div>
    </section>
  )
}
