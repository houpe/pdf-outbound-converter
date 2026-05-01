import './ui.css'

export default function Button({
  as: Comp = 'button',
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  className = '',
  children,
  ...props
}) {
  const isDisabled = Boolean(disabled || loading)
  const canDisable = Comp === 'button'

  const cls = [
    'ui-btn',
    `ui-btn--${variant}`,
    `ui-btn--${size}`,
    className,
  ].filter(Boolean).join(' ')

  return (
    <Comp
      className={cls}
      disabled={canDisable ? isDisabled : undefined}
      aria-disabled={isDisabled || undefined}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <span className="ui-btn__spinner" aria-hidden="true" />}
      <span className="ui-btn__label">{children}</span>
    </Comp>
  )
}

