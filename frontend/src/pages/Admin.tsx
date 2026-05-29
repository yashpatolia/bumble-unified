import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import type { ApiUsageStats } from '../types'

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
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null)

  const load = () =>
    api.apiUsage().then(u => { setUsage(u); setLastRefreshed(new Date()) }).catch(() => {})

  useEffect(() => {
    load()
    const id = setInterval(load, 30_000)
    return () => clearInterval(id)
  }, [])

  if (!usage) return <p className="text-muted" style={{ fontSize: 13 }}>Loading...</p>

  const limit = usage.rate_limit.requests
  const windowMin = usage.rate_limit.window_minutes
  const { local, hypixel } = usage

  const cards = [
    { label: 'Last Minute',    value: hypixel.queries_in_past_minute ?? local.last_minute, max: Math.round(limit / windowMin),        color: 'var(--accent)', sub: `of ~${Math.round(limit / windowMin)} / min` },
    { label: 'Last 5 Minutes', value: local.last_5min,                                     max: Math.round(limit / windowMin * 5),    color: '#5b8dd9',       sub: `of ~${Math.round(limit / windowMin * 5)} / 5 min` },
    { label: 'Last Hour',      value: local.last_hour,                                     max: Math.round(limit / windowMin * 60),   color: '#6fbf7e',       sub: `of ~${Math.round(limit / windowMin * 60)} / hour` },
    { label: 'Last 24 Hours',  value: local.today,                                         max: Math.round(limit / windowMin * 1440), color: '#c87d4a',       sub: `of ~${Math.round(limit / windowMin * 1440).toLocaleString()} / day` },
  ]

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 12 }}>
        <div className="events-section-label" style={{ margin: 0 }}>API Usage</div>
        <span className="text-muted" style={{ fontSize: 12 }}>
          Rate limit: {limit} req / {windowMin} min
          {lastRefreshed && ` · updated ${lastRefreshed.toLocaleTimeString()}`}
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 32 }}>
        {cards.map(c => (
          <div key={c.label} className="card" style={{ padding: '14px 16px' }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{c.label}</div>
            <div style={{ fontSize: 22, fontWeight: 600 }}>{c.value.toLocaleString()}</div>
            <UsageBar value={c.value} max={c.max} color={c.color} />
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>{c.sub}</div>
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
    </>
  )
}

export default function Admin() {
  const { me, loading, logout } = useAuth()
  const navigate = useNavigate()

  if (loading) return null
  if (!me?.is_owner) return <Navigate to="/" replace />

  return (
    <div className="guild-layout">
      <header className="guild-header">
        <div className="guild-header-left">
          <span className="guild-header-back" onClick={() => navigate('/')}>← All Guilds</span>
          <span className="guild-header-sep">/</span>
          <span className="guild-header-name">Admin</span>
        </div>

        <div className="guild-header-user">
          {me.avatar_url && (
            <img src={me.avatar_url} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
          )}
          <span>{me.discord_name}</span>
          <button className="btn btn-ghost btn-sm" onClick={() => { logout(); navigate('/login') }}>Logout</button>
        </div>
      </header>

      <main className="guild-main">
        <ApiUsagePanel />

        <div className="events-section-label">Management</div>
        <div className="guild-cards">
          <Link className="guild-card" to="/users">
            <div className="guild-card-header">
              <div>
                <div className="guild-card-name" style={{ fontSize: 18 }}>User Management</div>
                <div className="guild-card-tag">Add, edit, or remove panel users and their permissions</div>
              </div>
            </div>
            <div className="guild-card-footer">
              <span className="guild-enter">Manage Users →</span>
            </div>
          </Link>
        </div>
      </main>
    </div>
  )
}
