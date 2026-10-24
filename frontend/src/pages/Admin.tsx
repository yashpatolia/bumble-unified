import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { ArrowRightIcon } from '../components/icons'
import { usePolling } from '../hooks/usePolling'
import type { ApiUsageStats } from '../types'

function ApiUsagePanel() {
  const [usage, setUsage] = useState<ApiUsageStats | null>(null)
  const [updated, setUpdated] = useState<Date | null>(null)

  usePolling(() => {
    api.apiUsage().then(u => { setUsage(u); setUpdated(new Date()) }).catch(() => {})
  }, 30_000)

  if (!usage) return <p className="text-muted">Loading...</p>

  const limit = usage.rate_limit.requests
  const windowMin = usage.rate_limit.window_minutes
  const { local, hypixel } = usage
  const per = (mins: number) => Math.round((limit / windowMin) * mins)

  const cards = [
    { label: 'Last minute', value: hypixel.queries_in_past_minute ?? local.last_minute, max: per(1), sub: `of about ${per(1)} per minute` },
    { label: 'Last 5 minutes', value: local.last_5min, max: per(5), sub: `of about ${per(5)} per 5 min` },
    { label: 'Last hour', value: local.last_hour, max: per(60), sub: `of about ${per(60)} per hour` },
    { label: 'Last 24 hours', value: local.today, max: per(1440), sub: `of about ${per(1440).toLocaleString()} per day` },
  ]

  return (
    <>
      <div className="card-sub" style={{ marginBottom: 12 }}>
        Rate limit: {limit} requests per {windowMin} minutes{updated && `, updated ${updated.toLocaleTimeString()}`}
      </div>
      <div className="kpis">
        {cards.map((c, i) => {
          const pct = c.max > 0 ? Math.min(100, Math.round((c.value / c.max) * 100)) : 0
          return (
            <div key={c.label} className="card kpi reveal" style={{ '--i': i } as React.CSSProperties}>
              <div className="k-label">{c.label}</div>
              <div className="k-value num">{c.value.toLocaleString()}</div>
              <div className="meter"><i style={{ width: `${pct}%` }} /></div>
              <div className="k-sub" style={{ marginTop: 6 }}>{c.sub}</div>
            </div>
          )
        })}
      </div>
      {hypixel.total_queries != null && (
        <div className="card-sub">Lifetime calls on this API key: <b className="num">{hypixel.total_queries.toLocaleString()}</b></div>
      )}
    </>
  )
}

export default function Admin() {
  return (
    <div>
      <div className="crumb reveal">Tools / Admin</div>
      <div className="page-head reveal" style={{ '--i': 1 } as React.CSSProperties}>
        <h1 className="page-title">Admin</h1>
      </div>

      <div className="section-label">Hypixel API usage</div>
      <ApiUsagePanel />

      <div className="section-label">Management</div>
      <div className="guild-cards">
        <Link className="card guild-card reveal" to="/users">
          <div className="g-name" style={{ fontSize: 21, marginTop: 0 }}>Panel users</div>
          <div className="text-muted">Add, edit, or remove panel users and their permissions.</div>
          <div className="g-foot">Manage users <ArrowRightIcon width={16} height={16} /></div>
        </Link>
      </div>
    </div>
  )
}
