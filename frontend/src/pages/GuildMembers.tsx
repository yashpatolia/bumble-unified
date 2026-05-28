import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import type { GuildMember } from '../types'

const CACHE_TTL = 5 * 60 * 1000
const cache = new Map<string, { members: GuildMember[]; at: number }>()

type SortKey = 'ign' | 'rank' | 'level' | 'last_login' | 'status'
type SortDir = 'asc' | 'desc'

function formatLastLogin(ts: number | null): string {
  if (!ts) return 'N/A'
  const diff = Date.now() - ts
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(diff / 3600000)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(diff / 86400000)
  if (days < 30) return `${days}d ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months}mo ago`
  return `${Math.floor(months / 12)}y ago`
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span style={{ opacity: 0.3, marginLeft: 4 }}>↕</span>
  return <span style={{ marginLeft: 4 }}>{dir === 'asc' ? '↑' : '↓'}</span>
}

export default function GuildMembers() {
  const { key } = useParams<{ key: string }>()
  const { me } = useAuth()
  const canFetch = me?.can_fetch_api || me?.is_admin || me?.is_owner

  const cached = key ? cache.get(key) : undefined
  const [members, setMembers] = useState<GuildMember[]>(cached?.members ?? [])
  const [loading, setLoading] = useState(!cached)
  const [error, setError] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>('status')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [refreshing, setRefreshing] = useState(false)
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = (force = false) => {
    if (!key) return
    const hit = cache.get(key)
    if (!force && hit && Date.now() - hit.at < CACHE_TTL) {
      setMembers(hit.members)
      return
    }
    setLoading(true)
    setError(null)
    api.guildMembers(key)
      .then(res => {
        cache.set(key, { members: res.members, at: Date.now() })
        setMembers(res.members)
      })
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load members'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [key])

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const refreshStats = async () => {
    if (!key || refreshing) return
    setRefreshing(true)
    setRefreshMsg(null)
    try {
      const res = await api.refreshStats(key)
      if (res.status === 'already_running') {
        setRefreshMsg('Already fetching...')
        setRefreshing(false)
        return
      }
      const est = res.total * 2
      setRefreshMsg(`Fetching stats for ${res.total} members (~${est}s)...`)
      // Poll until done
      pollRef.current = setInterval(async () => {
        try {
          const s = await api.statsStatus(key)
          if (!s.fetching) {
            clearInterval(pollRef.current!)
            pollRef.current = null
            setRefreshing(false)
            setRefreshMsg('Done! Refreshing list...')
            cache.delete(key)
            load(true)
            setTimeout(() => setRefreshMsg(null), 3000)
          }
        } catch {}
      }, 5000)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Refresh failed')
      setRefreshing(false)
    }
  }

  const handleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(k); setSortDir('asc') }
  }

  const sorted = [...members].sort((a, b) => {
    let cmp = 0
    if (sortKey === 'ign') cmp = a.ign.localeCompare(b.ign)
    else if (sortKey === 'rank') cmp = a.rank.localeCompare(b.rank)
    else if (sortKey === 'level') cmp = (a.skyblock_level ?? -1) - (b.skyblock_level ?? -1)
    else if (sortKey === 'last_login') cmp = (a.last_login ?? 0) - (b.last_login ?? 0)
    else if (sortKey === 'status') cmp = (a.online ? 1 : 0) - (b.online ? 1 : 0)
    return sortDir === 'asc' ? cmp : -cmp
  })

  const online = members.filter(m => m.online).length

  return (
    <div>
      <div className="header-row">
        <div className="page-title" style={{ marginBottom: 0 }}>
          Guild Members
          {members.length > 0 && (
            <span className="text-muted" style={{ fontSize: 14, fontWeight: 400, marginLeft: 10 }}>
              {online} online · {members.length} total
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {refreshMsg && <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{refreshMsg}</span>}
          {canFetch && (
            <button className="btn btn-ghost" onClick={refreshStats} disabled={refreshing}>
              {refreshing ? 'Fetching...' : 'Refresh Stats'}
            </button>
          )}
          <button className="btn btn-ghost" onClick={() => load(true)} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && <p style={{ color: 'var(--red)', marginBottom: 16 }}>{error}</p>}

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          {loading ? (
            <p className="empty">Fetching guild list from Minecraft...</p>
          ) : sorted.length === 0 ? (
            <p className="empty">No members found.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th style={{ cursor: 'pointer' }} onClick={() => handleSort('ign')}>
                    IGN <SortIcon active={sortKey === 'ign'} dir={sortDir} />
                  </th>
                  <th style={{ cursor: 'pointer' }} onClick={() => handleSort('rank')}>
                    Rank <SortIcon active={sortKey === 'rank'} dir={sortDir} />
                  </th>
                  <th style={{ cursor: 'pointer' }} onClick={() => handleSort('level')}>
                    Level <SortIcon active={sortKey === 'level'} dir={sortDir} />
                  </th>
                  <th style={{ cursor: 'pointer' }} onClick={() => handleSort('last_login')}>
                    Last Login <SortIcon active={sortKey === 'last_login'} dir={sortDir} />
                  </th>
                  <th style={{ cursor: 'pointer' }} onClick={() => handleSort('status')}>
                    Status <SortIcon active={sortKey === 'status'} dir={sortDir} />
                  </th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((m, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{m.ign}</td>
                    <td className="text-muted">{m.rank}</td>
                    <td className="text-muted">{m.skyblock_level != null ? m.skyblock_level.toFixed(1) : 'N/A'}</td>
                    <td className="text-muted">{formatLastLogin(m.last_login)}</td>
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
