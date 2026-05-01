import './ui.css'

export default function Card({
  as: Comp = 'section',
  variant = 'default',
  className = '',
  title,
  subtitle,
  headerRight,
  children,
  ...props
}) {
  const cls = [
    'ui-card',
    variant === 'muted' ? 'ui-card--muted' : '',
    className,
  ].filter(Boolean).join(' ')

  const showHeader = title || subtitle || headerRight

  return (
    <Comp className={cls} {...props}>
      {showHeader && (
        <div className="ui-card__header">
          <div>
            {title && <h3 className="ui-card__title">{title}</h3>}
            {subtitle && <p className="ui-card__subtitle">{subtitle}</p>}
          </div>
          {headerRight && <div>{headerRight}</div>}
        </div>
      )}
      {children}
    </Comp>
  )
}

