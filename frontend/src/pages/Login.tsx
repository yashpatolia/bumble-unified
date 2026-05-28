import { useEffect, useState } from 'react'

const FEATURES = [
  {
    icon: '⬡',
    title: 'Guild Overview',
    desc: 'Monitor member count, recent chat, and guild events across both BK and BU in real time.',
  },
  {
    icon: '◈',
    title: 'Member Management',
    desc: 'Browse all guild members with Skyblock level, last login, and online status at a glance.',
  },
  {
    icon: '▸',
    title: 'Bot Control',
    desc: 'Start, stop, and restart Mineflayer bots from the panel without touching the server.',
  },
  {
    icon: '≡',
    title: 'Live Logs',
    desc: 'Stream real-time logs from both bot processes with level filtering and text search.',
  },
]

export default function Login() {
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const e = params.get('error')
    if (e === 'oauth_denied') setError('Login was cancelled.')
    else if (e === 'oauth_failed') setError('Discord login failed. Try again.')
  }, [])

  return (
    <div className="landing">
      <div className="landing-hero">
        <div className="landing-logo">✦</div>
        <h1 className="landing-title">Bumble</h1>
        <p className="landing-sub">Guild management and monitoring panel for Bumble Kindergarten &amp; Bumble University.</p>
        {error && <p className="login-error" style={{ marginBottom: 8 }}>{error}</p>}
        <a href="/auth/discord" className="btn btn-discord landing-cta">
          <svg width="20" height="20" viewBox="0 0 127.14 96.36" fill="currentColor" style={{ flexShrink: 0 }}>
            <path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1A105.25,105.25,0,0,0,126.6,80.22h0C129.24,52.84,122.09,29.11,107.7,8.07ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,46,53.89,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,46,96.12,53,91.08,65.69,84.69,65.69Z"/>
          </svg>
          Continue with Discord
        </a>
        <p className="landing-hint">Access is restricted to authorized users only.</p>
      </div>

      <div className="landing-features">
        {FEATURES.map(f => (
          <div key={f.title} className="landing-feature-card">
            <div className="landing-feature-icon">{f.icon}</div>
            <div className="landing-feature-title">{f.title}</div>
            <div className="landing-feature-desc">{f.desc}</div>
          </div>
        ))}
      </div>

      <div className="landing-footer">
        Bumble Bridge Bot · Hypixel Skyblock
      </div>
    </div>
  )
}
