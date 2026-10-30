import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'

/** Overlay + card wrapper shared by every "form in a modal" flow (closes on
 * backdrop click). Callers own their own form fields and action buttons.
 * Rendered into <body>: inside an animated .reveal card the transform makes
 * position: fixed relative to the card, so the modal would open mid-page. */
export function Modal({ title, onClose, error, children, actions }: {
  title: ReactNode
  onClose: () => void
  error?: string | null
  children: ReactNode
  actions: ReactNode
}) {
  return createPortal(
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal">
        <div className="modal-title">{title}</div>
        {error && <p className="error-text">{error}</p>}
        {children}
        <div className="modal-actions">{actions}</div>
      </div>
    </div>,
    document.body,
  )
}
