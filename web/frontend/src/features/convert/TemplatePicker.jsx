import { IconCheck } from '../../Icons'

export default function TemplatePicker({
  templates,
  templateKey,
  onChange,
  disabled = false,
}) {
  return (
    <div className="convert-template-grid">
      {Object.entries(templates).map(([key, t]) => (
        <button
          key={key}
          className={`convert-template-btn ${templateKey === key ? 'active' : ''}`}
          onClick={() => onChange(key)}
          type="button"
          disabled={disabled}
        >
          <span className="convert-template-btn__check">
            {templateKey === key ? <IconCheck /> : null}
          </span>
          <span className="convert-template-btn__info">
            <span className="convert-template-btn__name">{t.name}</span>
            <span className="convert-template-btn__accept">
              支持 {t.accept?.replace(/,/g, ' / ')}
            </span>
          </span>
        </button>
      ))}
    </div>
  )
}
