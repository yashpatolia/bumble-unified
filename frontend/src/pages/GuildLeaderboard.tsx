import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import { DiscordIdentityCell, PlayerIdentityCell } from '../components/IdentityCell'
import type { LevelLeaderboardData, LevelPerson } from '../types'

type Period = 'lifetime' | 'month' | 'week'

interface Entry {
  ign: string
  count: number
  uuid: string | null
  discord_name: string | null
  discord_id: string | null
  discord_avatar: string | null
}

const PERIODS: { id: Period; label: string }[] = [
  { id: 'lifetime', label: 'All time' },
  { id: 'month', label: 'This month' },
  { id: 'week', label: 'This week' },
]

function MessagesBoard({ key_ }: { key_: string }) {
  const key = key_
  const [period, setPeriod] = useState<Period>('lifetime')
  const [data, setData] = useState<Entry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!key) return
    setLoading(true)
    setError(null)
    api.leaderboard(key, period)
      .then(r => setData(r.leaderboard))
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [key, period])

  const top = data[0]?.count ?? 0

  return (
    <div>
      <div className="head-actions" style={{ marginBottom: 14 }}>
        <div className="tabs">
          {PERIODS.map(p => (
            <button key={p.id} className={`tab${period === p.id ? ' active' : ''}`} onClick={() => setPeriod(p.id)}>{p.label}</button>
          ))}
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="card">
        <div className="table-wrap">
          {loading ? (
            <p className="empty">Loading...</p>
          ) : data.length === 0 ? (
            <p className="empty">No messages recorded yet.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th style={{ width: 56 }}>#</th>
                  <th>Player</th>
                  <th>Discord</th>
                  <th style={{ textAlign: 'right' }}>Messages</th>
                </tr>
              </thead>
              <tbody>
                {data.map((entry, i) => (
                  <tr key={entry.uuid || entry.ign}>
                    <td><span className={`rank-pill${i < 3 ? ' top' : ''}`}>{i + 1}</span></td>
                    <td><PlayerIdentityCell uuid={entry.uuid} ign={entry.ign} /></td>
                    <td><DiscordIdentityCell name={entry.discord_name} avatar={entry.discord_avatar} /></td>
                    <td style={{ textAlign: 'right', minWidth: 160 }}>
                      <div className="num" style={{ fontWeight: 700 }}>{entry.count.toLocaleString()}</div>
                      <div className="meter" style={{ marginTop: 4, marginLeft: 'auto', width: 120 }}><i style={{ width: `${top ? (entry.count / top) * 100 : 0}%` }} /></div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

const WINDOWS = [
  { id: 7, label: '7 days' },
  { id: 30, label: '30 days' },
  { id: 90, label: '90 days' },
]

function LevelsBoard({ key_ }: { key_: string }) {
  const [mode, setMode] = useState<'top' | 'climbers'>('climbers')
  const [days, setDays] = useState(30)
  const [data, setData] = useState<LevelLeaderboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.levelLeaderboard(key_, days)
      .then(setData)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [key_, days])

  const rows: LevelPerson[] = (mode === 'top' ? data?.top : data?.climbers) ?? []
  const best = mode === 'top' ? (rows[0]?.level ?? 0) : (rows[0]?.gain ?? 0)

  return (
    <div>
      <div className="head-actions" style={{ marginBottom: 14, justifyContent: 'space-between', width: '100%' }}>
        <div className="tabs">
          <button className={`tab${mode === 'climbers' ? ' active' : ''}`} onClick={() => setMode('climbers')}>Fastest climbers</button>
          <button className={`tab${mode === 'top' ? ' active' : ''}`} onClick={() => setMode('top')}>Highest level</button>
        </div>
        {mode === 'climbers' && (
          <div className="tabs">
            {WINDOWS.map(w => (
              <button key={w.id} className={`tab${days === w.id ? ' active' : ''}`} onClick={() => setDays(w.id)}>{w.label}</button>
            ))}
          </div>
        )}
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="card">
        <div className="table-wrap">
          {loading ? (
            <p className="empty">Loading...</p>
          ) : rows.length === 0 ? (
            <p className="empty">{mode === 'climbers' ? 'No level gains recorded for this window yet. Level history builds up one snapshot per member per day.' : 'No levels recorded yet.'}</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th style={{ width: 56 }}>#</th>
                  <th>Player</th>
                  <th>Discord</th>
                  <th className="hide-sm">Rank</th>
                  <th style={{ textAlign: 'right' }}>{mode === 'top' ? 'Level' : `Levels gained, ${days}d`}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p, i) => {
                  const value = mode === 'top' ? p.level : (p.gain ?? 0)
                  const partial = mode === 'climbers' && p.days_covered != null && p.days_covered < days
                  return (
                    <tr key={p.ign}>
                      <td><span className={`rank-pill${i < 3 ? ' top' : ''}`}>{i + 1}</span></td>
                      <td><PlayerIdentityCell uuid={p.uuid} ign={p.ign} /></td>
                      <td><DiscordIdentityCell name={p.discord_name} avatar={p.discord_avatar} /></td>
                      <td className="text-muted hide-sm">{p.rank}</td>
                      <td style={{ textAlign: 'right', minWidth: 170 }}>
                        <div className={`num ${mode === 'climbers' ? 'gain-up' : ''}`} style={{ fontWeight: 700 }}>
                          {mode === 'climbers' ? '+' : ''}{value.toFixed(1)}
                          {mode === 'top' && p.gain != null && p.gain !== 0 && (
                            <span className={p.gain > 0 ? 'gain-up' : 'gain-down'} style={{ marginLeft: 8, fontSize: 12 }}>{p.gain > 0 ? '+' : ''}{p.gain.toFixed(1)} in {days}d</span>
                          )}
                        </div>
                        {partial && <div className="card-sub">over {p.days_covered}d of history</div>}
                        <div className="meter" style={{ marginTop: 4, marginLeft: 'auto', width: 120 }}><i style={{ width: `${best ? (value / best) * 100 : 0}%` }} /></div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

export default function GuildLeaderboard() {
  const { key } = useParams<{ key: string }>()
  const [view, setView] = useState<'messages' | 'levels'>('levels')
  if (!key) return null

  return (
    <div>
      <div className="crumb reveal">{key.toUpperCase()} / Leaderboard</div>
      <div className="page-head reveal" style={{ '--i': 1 } as React.CSSProperties}>
        <h1 className="page-title">Leaderboards</h1>
        <div className="tabs">
          <button className={`tab${view === 'levels' ? ' active' : ''}`} onClick={() => setView('levels')}>Levels</button>
          <button className={`tab${view === 'messages' ? ' active' : ''}`} onClick={() => setView('messages')}>Messages</button>
        </div>
      </div>
      <div className="reveal" style={{ '--i': 2 } as React.CSSProperties}>
        {view === 'levels' ? <LevelsBoard key_={key} /> : <MessagesBoard key_={key} />}
      </div>
    </div>
  )
}
