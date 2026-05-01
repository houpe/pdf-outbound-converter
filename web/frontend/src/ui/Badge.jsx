import './ui.css'

export default function Badge({
  as: Comp = 'span',
  variant = 'info',
  className = '',
  children,
  ...props
}) {
  const cls = [
    'ui-badge',
    `ui-badge--${variant}`,
    className,
  ].filter(Boolean).join(' ')

  return (
    <Comp className={cls} {...props}>
      {children}
    </Comp>
  )
}

