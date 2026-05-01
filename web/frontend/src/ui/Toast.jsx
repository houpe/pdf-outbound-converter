import './ui.css'

function ToastItem({
  id,
  title,
  message,
  variant = 'info',
  onClose,
  closeLabel = '关闭',
}) {
  return (
    <div className={['ui-toast', `ui-toast--${variant}`].join(' ')} role="status" aria-live="polite">
      <div>
        {title && <p className="ui-toast__title">{title}</p>}
        {message && <p className="ui-toast__message">{message}</p>}
      </div>
      <button
        className="ui-toast__close"
        type="button"
        onClick={() => onClose?.(id)}
        aria-label={closeLabel}
      >
        ✕
      </button>
    </div>
  )
}

export default function ToastViewport({
  toasts = [],
  onClose,
  className = '',
}) {
  if (!toasts || toasts.length === 0) return null

  return (
    <div className={['ui-toast-viewport', className].filter(Boolean).join(' ')}>
      {toasts.map(t => (
        <ToastItem key={t.id} {...t} onClose={onClose} />
      ))}
    </div>
  )
}

export { ToastItem }

