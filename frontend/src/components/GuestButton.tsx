import { useState } from 'react'
import { startGuestSession } from '../api'

/** "Continue as guest": starts a read-only session, then reloads into the app. */
export function GuestButton({ className = 'btn' }: { className?: string }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const go = async () => {
    setBusy(true)
    setError(null)
    try {
      await startGuestSession()
      window.location.href = '/'
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed')
      setBusy(false)
    }
  }

  return (
    <>
      <button className={className} onClick={go} disabled={busy}>{busy ? 'Starting...' : 'Continue as guest'}</button>
      {error && <span className="error-text" style={{ margin: 0 }}>{error}</span>}
    </>
  )
}
