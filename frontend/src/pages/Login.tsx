import { useEffect, useState } from 'react'

export default function Login() {
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const e = params.get('error')
    if (e === 'oauth_denied') setError('Login was cancelled.')
    else if (e === 'oauth_failed') setError('Discord login failed. Try again.')
    else {
      // No error — auto-redirect to Discord OAuth
      window.location.href = '/auth/discord'
    }
  }, [])

  return (
    <div className="login-page">
      <div className="login-box">
        <div className="login-title">Bumble</div>
        <div className="login-sub">Guild management &amp; monitoring</div>
        {error ? (
          <>
            <div className="login-error">{error}</div>
            <a href="/auth/discord" className="btn btn-discord" style={{ display: 'inline-flex', width: '100%', justifyContent: 'center', marginTop: 16 }}>
              Try again
            </a>
          </>
        ) : (
          <div style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 8 }}>Redirecting to Discord...</div>
        )}
      </div>
    </div>
  )
}
