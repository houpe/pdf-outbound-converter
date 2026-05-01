import './ui.css'

const clamp01 = (n) => Math.max(0, Math.min(1, n))

export default function Progress({
  value = 0,
  max = 100,
  label,
  showValue = true,
  className = '',
  ...props
}) {
  const maxSafe = max || 100
  const ratio = clamp01(Number(value) / Number(maxSafe))
  const pct = Math.round(ratio * 100)

  return (
    <div className={['ui-progress', className].filter(Boolean).join(' ')} {...props}>
      {(label || showValue) && (
        <div className="ui-progress__top">
          {label ? <p className="ui-progress__label">{label}</p> : <span />}
          {showValue && <span className="ui-progress__value">{pct}%</span>}
        </div>
      )}

      <div
        className="ui-progress__track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={maxSafe}
        aria-valuenow={Number.isFinite(Number(value)) ? Number(value) : 0}
        aria-label={label || '进度'}
      >
        <div className="ui-progress__bar" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

