import type { ReactNode } from 'react'

/** Overlay + card wrapper shared by every "form in a modal" flow (closes on
 * backdrop click). Callers own their own form fields and action buttons. */
export function Modal({ title, onClose, error, children, actions }: {
  title: ReactNode
  onClose: () => void
  error?: string | null
  children: ReactNode
  actions: ReactNode
}) {
  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal">
        <div className="modal-title">{title}</div>
        {error && <p style={{ color: 'var(--red)', marginBottom: 12, fontSize: 13 }}>{error}</p>}
        {children}
        <div className="modal-actions">{actions}</div>
      </div>
    </div>
  )
}
