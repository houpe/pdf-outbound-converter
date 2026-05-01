import { Dialog } from '@headlessui/react'
import './ui.css'

export default function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  className = '',
  closeLabel = '关闭',
}) {
  return (
    <Dialog open={Boolean(open)} onClose={onClose} className="ui-modal__overlay">
      <Dialog.Panel className={['ui-modal', className].filter(Boolean).join(' ')}>
        {(title || onClose) && (
          <header className="ui-modal__header">
            {title ? (
              <Dialog.Title className="ui-modal__title">{title}</Dialog.Title>
            ) : (
              <span />
            )}
            {onClose && (
              <button className="ui-modal__close" type="button" onClick={onClose} aria-label={closeLabel}>
                ✕
              </button>
            )}
          </header>
        )}

        <div className="ui-modal__body">
          {children}
        </div>

        {footer && (
          <footer className="ui-modal__footer">
            {footer}
          </footer>
        )}
      </Dialog.Panel>
    </Dialog>
  )
}

