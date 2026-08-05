import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import { DiscordIdentityCell, PlayerIdentityCell } from '../components/IdentityCell'

type Period = 'lifetime' | 'month' | 'week'

interface Entry {
  ign: string
  count: number
  uuid: string | null
  discord_name: string | null
  discord_id: string | null
  discord_avatar: string | null
}

export default function GuildLeaderboard() {
  const { key } = useParams<{ key: string }>()
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

  return (
    <div>
      <div className="header-row">
        <div className="page-title" style={{ marginBottom: 0 }}>Message Leaderboard</div>
        <div style={{ display: 'flex', gap: 6 }}>
          {(['lifetime', 'month', 'week'] as Period[]).map(p => (
            <button
              key={p}
              className={`btn ${period === p ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setPeriod(p)}
            >
              {p === 'lifetime' ? 'All Time' : p === 'month' ? 'This Month' : 'This Week'}
            </button>
          ))}
        </div>
      </div>

      {error && <p style={{ color: 'var(--red)', marginBottom: 16 }}>{error}</p>}

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          {loading ? (
            <p className="empty">Loading...</p>
          ) : data.length === 0 ? (
            <p className="empty">No messages recorded yet.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th style={{ width: 48 }}>#</th>
                  <th>IGN</th>
                  <th>Discord</th>
                  <th style={{ textAlign: 'right' }}>Messages</th>
                </tr>
              </thead>
              <tbody>
                {data.map((entry, i) => (
                  <tr key={entry.uuid || entry.ign}>
                    <td style={{ color: 'var(--muted)', fontWeight: 500 }}>
                      {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}
                    </td>
                    <td>
                      <PlayerIdentityCell uuid={entry.uuid} ign={entry.ign} />
                    </td>
                    <td>
                      <DiscordIdentityCell name={entry.discord_name} avatar={entry.discord_avatar} id={entry.discord_id} />
                    </td>
                    <td style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: 'var(--text-secondary)' }}>
                      {entry.count.toLocaleString()}
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
