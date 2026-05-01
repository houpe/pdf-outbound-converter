import { useCallback, useEffect, useRef, useState } from 'react'

let _seq = 0

const nextId = () => {
  _seq = (_seq + 1) % Number.MAX_SAFE_INTEGER
  return `${Date.now()}_${_seq}`
}

/**
 * 轻量 toast 状态管理（无业务逻辑，无外部依赖）。
 *
 * 建议搭配 src/ui/Toast.jsx 的 <ToastViewport toasts={toasts} onClose={dismissToast} />
 */
export default function useToast({ duration = 3000, limit = 3 } = {}) {
  const [toasts, setToasts] = useState([])
  const timersRef = useRef(new Map())

  const dismissToast = useCallback((id) => {
    if (!id) return
    const t = timersRef.current.get(id)
    if (t) {
      clearTimeout(t)
      timersRef.current.delete(id)
    }
    setToasts(prev => prev.filter(x => x.id !== id))
  }, [])

  const clearToasts = useCallback(() => {
    timersRef.current.forEach(t => clearTimeout(t))
    timersRef.current.clear()
    setToasts([])
  }, [])

  const pushToast = useCallback((input) => {
    const id = nextId()
    const item = typeof input === 'string'
      ? { id, message: input, variant: 'info' }
      : { id, variant: 'info', ...input }

    setToasts(prev => [item, ...prev].slice(0, Math.max(1, limit)))

    const d = Number.isFinite(Number(item.duration)) ? Number(item.duration) : duration
    if (d > 0) {
      const timer = setTimeout(() => dismissToast(id), d)
      timersRef.current.set(id, timer)
    }

    return id
  }, [dismissToast, duration, limit])

  useEffect(() => () => {
    timersRef.current.forEach(t => clearTimeout(t))
    timersRef.current.clear()
  }, [])

  return { toasts, pushToast, dismissToast, clearToasts }
}

