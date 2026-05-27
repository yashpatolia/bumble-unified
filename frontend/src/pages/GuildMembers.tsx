import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import type { GuildMember } from '../types'

export default function GuildMembers() {
  const { key } = useParams<{ key: string }>()
  const [members, setMembers] = useState<GuildMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    if (!key) return
    setLoading(true)
    setError(null)
    api.guildMembers(key)
      .then(res => setMembers(res.members))
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load members'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [key])

  const online = members.filter(m => m.online)
  const offline = members.filter(m => !m.online)
  const sorted = [...online, ...offline]

  return (
    <div>
      <div className="header-row">
        <div className="page-title" style={{ marginBottom: 0 }}>
          Guild Members
          {members.length > 0 && (
            <span className="text-muted" style={{ fontSize: 14, fontWeight: 400, marginLeft: 10 }}>
              {online.length} online · {members.length} total
            </span>
          )}
        </div>
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {error && <p style={{ color: 'var(--red)', marginBottom: 16 }}>{error}</p>}

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          {loading ? (
            <p className="empty">Fetching guild list from Minecraft...</p>
          ) : sorted.length === 0 ? (
            <p className="empty">No members found. Bot may be offline.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>IGN</th>
                  <th>Rank</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((m, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{m.ign}</td>
                    <td className="text-muted">{m.rank}</td>
                    <td>
                      {m.online
                        ? <span className="badge badge-online">Online</span>
                        : <span className="badge badge-off">Offline</span>
                      }
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
