import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import type { ApiUsageStats, GuildStatus } from '../types'

const FALLBACK: GuildStatus[] = [
  { key: 'bk', name: 'Bumble Kindergarten', short_name: 'BK', username: '—', connected: false },
  { key: 'bu', name: 'Bumble University',   short_name: 'BU', username: '—', connected: false },
]

function UsageBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-secondary)', marginBottom: 3 }}>
        <span>{value} calls</span>
        <span>{pct}%</span>
      </div>
      <div style={{ height: 4, background: 'var(--surface3)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 2, transition: 'width 0.4s ease' }} />
      </div>
    </div>
  )
}

function ApiUsagePanel() {
  const [usage, setUsage] = useState<ApiUsageStats | null>(null)

  useEffect(() => {
    api.apiUsage().then(setUsage).catch(() => {})
    const id = setInterval(() => api.apiUsage().then(setUsage).catch(() => {}), 30_000)
    return () => clearInterval(id)
  }, [])

  if (!usage) return null

  const limit = usage.rate_limit.requests
  const windowMin = usage.rate_limit.window_minutes
  const { local, hypixel } = usage

  const usageCards = [
    {
      label: 'Last Minute',
      value: hypixel.queries_in_past_minute ?? local.last_minute,
      max: Math.round(limit / windowMin),
      color: 'var(--accent)',
      sublabel: `of ~${Math.round(limit / windowMin)} / min budget`,
    },
    {
      label: 'Last 5 Minutes',
      value: local.last_5min,
      max: Math.round(limit / windowMin * 5),
      color: '#5b8dd9',
      sublabel: `of ~${Math.round(limit / windowMin * 5)} / 5 min`,
    },
    {
      label: 'Last Hour',
      value: local.last_hour,
      max: Math.round(limit / windowMin * 60),
      color: '#6fbf7e',
      sublabel: `of ~${Math.round(limit / windowMin * 60)} / hour`,
    },
    {
      label: 'Last 24 Hours',
      value: local.today,
      max: Math.round(limit / windowMin * 60 * 24),
      color: '#c87d4a',
      sublabel: `of ~${Math.round(limit / windowMin * 60 * 24).toLocaleString()} / day`,
    },
  ]

  return (
    <div style={{ marginBottom: 40 }}>
      <div className="events-section-label" style={{ marginBottom: 12 }}>
        API Usage
        <span className="text-muted" style={{ fontSize: 12, fontWeight: 400, marginLeft: 10 }}>
          Rate limit: {limit} req / {windowMin} min · refreshes every 30s
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
        {usageCards.map(c => (
          <div key={c.label} className="card" style={{ padding: '14px 16px' }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{c.label}</div>
            <div style={{ fontSize: 22, fontWeight: 600 }}>{c.value.toLocaleString()}</div>
            <UsageBar value={c.value} max={c.max} color={c.color} />
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>{c.sublabel}</div>
          </div>
        ))}
        {hypixel.total_queries != null && (
          <div className="card" style={{ padding: '14px 16px' }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>Total Queries (Hypixel)</div>
            <div style={{ fontSize: 22, fontWeight: 600 }}>{hypixel.total_queries.toLocaleString()}</div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 10 }}>Lifetime calls on this API key</div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Home() {
  const { me, logout } = useAuth()
  const navigate = useNavigate()
  const [bots, setBots] = useState<GuildStatus[]>([])

  useEffect(() => {
    api.bots()
      .then(data => setBots(Object.values(data)))
      .catch(() => {})
    const id = setInterval(() =>
      api.bots().then(data => setBots(Object.values(data))).catch(() => {}), 15_000)
    return () => clearInterval(id)
  }, [])

  const guildList = bots.length > 0 ? bots : FALLBACK

  return (
    <div className="home-page">
      <header className="home-header">
        <div className="home-logo">Bumble</div>
        <div className="home-user">
          {me?.avatar_url && (
            <img src={me.avatar_url} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
          )}
          <span>{me?.discord_name}</span>
          {me?.is_owner && (
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/users')}>Admin</button>
          )}
          <button className="btn btn-ghost btn-sm" onClick={() => { logout(); navigate('/login') }}>Logout</button>
        </div>
      </header>

      <div className="home-body">
        <div className="home-title">Welcome back{me?.discord_name ? `, ${me.discord_name}` : ''}</div>
        <div className="home-sub">Select a guild to view its overview, or browse cross-guild events.</div>

        <div className="events-section-label">Guilds</div>
        <div className="guild-cards" style={{ marginBottom: 40 }}>
          {guildList.map(bot => (
            <Link key={bot.key} className="guild-card" to={`/guilds/${bot.key}`}>
              <div className="guild-card-header">
                <div>
                  <div className="guild-card-name">{bot.name}</div>
                  <div className="guild-card-tag">{bot.username}</div>
                </div>
                <div className="guild-card-status">
                  <span className={`status-dot ${bot.connected ? 'online' : 'offline'}`} />
                  {bot.connected ? 'Online' : 'Offline'}
                </div>
              </div>
              <div className="guild-card-footer">
                <span className="guild-enter">View Guild →</span>
              </div>
            </Link>
          ))}
        </div>

        {(me?.is_admin || me?.is_owner) && <ApiUsagePanel />}

        <div className="events-section-label">Events</div>
        <div className="guild-cards">
          <Link className="guild-card" to="/events">
            <div className="guild-card-header">
              <div>
                <div className="guild-card-name" style={{ fontSize: 18 }}>Guild Events</div>
                <div className="guild-card-tag">Challenges and competitions across BK, BU, or both guilds</div>
              </div>
              <span className="badge badge-user" style={{ whiteSpace: 'nowrap', marginTop: 3 }}>Coming Soon</span>
            </div>
            <div className="guild-card-footer">
              <span className="guild-enter">View Events →</span>
            </div>
          </Link>
        </div>
      </div>
    </div>
  )
}
