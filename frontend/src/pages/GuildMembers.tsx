import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import type { GuildMember } from '../types'

const CACHE_TTL = 5 * 60 * 1000
const cache = new Map<string, { members: GuildMember[]; at: number }>()

const BOTTOM_N = 20
const DAY_MS = 86400000

type WarnLevel = 'yellow' | 'orange' | 'red'

const WARN_STYLES: Record<WarnLevel, { background: string; color: string; border: string; label: string }> = {
  yellow: { background: 'rgba(255,200,0,0.12)', color: '#e6b800', border: '1px solid rgba(255,200,0,0.3)', label: 'Low Activity' },
  orange: { background: 'rgba(255,140,0,0.12)', color: '#ff8c00', border: '1px solid rgba(255,140,0,0.3)', label: 'Inactive' },
  red:    { background: 'rgba(255,60,60,0.12)',  color: '#ff4444', border: '1px solid rgba(255,60,60,0.3)',  label: 'Kick Risk' },
}

function getWarnLevel(m: GuildMember, bottomIgns: Set<string>): WarnLevel | null {
  if (!bottomIgns.has(m.ign) || m.last_login == null) return null
  const days = (Date.now() - m.last_login) / DAY_MS
  if (days > 60) return 'red'
  if (days > 30) return 'orange'
  if (days > 14) return 'yellow'
  return null
}

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
  const canManageLinks = me?.can_manage_links || me?.is_admin || me?.is_owner

  const cached = key ? cache.get(key) : undefined
  const [members, setMembers] = useState<GuildMember[]>(cached?.members ?? [])
  const [loading, setLoading] = useState(!cached)
  const [error, setError] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>('status')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [refreshing, setRefreshing] = useState(false)
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null)
  const [refreshProgress, setRefreshProgress] = useState<{ done: number; total: number } | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Link modal state
  const [linkTarget, setLinkTarget] = useState<GuildMember | null>(null)
  const [linkForm, setLinkForm] = useState({ discord_id: '', discord_name: '' })
  const [linkSaving, setLinkSaving] = useState(false)
  const [linkError, setLinkError] = useState<string | null>(null)

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

  const startPolling = (k: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const s = await api.statsStatus(k)
        if (s.total > 0) setRefreshProgress({ done: s.done, total: s.total })
        if (!s.fetching) {
          clearInterval(pollRef.current!)
          pollRef.current = null
          setRefreshing(false)
          setRefreshProgress(null)
          setRefreshMsg('Done! Refreshing list...')
          cache.delete(k)
          load(true)
          setTimeout(() => setRefreshMsg(null), 3000)
        }
      } catch {}
    }, 3000)
  }

  useEffect(() => {
    if (!key || !canFetch) return
    api.statsStatus(key).then(s => {
      if (!s.fetching) return
      setRefreshing(true)
      setRefreshMsg('Fetching stats in progress...')
      if (s.total > 0) setRefreshProgress({ done: s.done, total: s.total })
      startPolling(key)
    }).catch(() => {})
  }, [key])

  const refreshStats = async () => {
    if (!key || refreshing) return
    setRefreshing(true)
    setRefreshMsg(null)
    setRefreshProgress(null)
    try {
      const res = await api.refreshStats(key)
      if (res.status === 'already_running') {
        setRefreshMsg('Already fetching...')
        setRefreshing(false)
        return
      }
      setRefreshMsg(`Fetching stats for ${res.total} members...`)
      setRefreshProgress({ done: 0, total: res.total })
      startPolling(key)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Refresh failed')
      setRefreshing(false)
    }
  }

  const handleSort = (k: SortKey) => {
    if (sortKey === k) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(k)
      setSortDir(k === 'last_login' || k === 'level' || k === 'status' ? 'desc' : 'asc')
    }
  }

  const openLink = (m: GuildMember) => {
    setLinkTarget(m)
    setLinkForm({ discord_id: m.discord_id ?? '', discord_name: m.discord_name ?? '' })
    setLinkError(null)
  }

  const saveLink = async () => {
    if (!key || !linkTarget) return
    if (!/^\d{17,20}$/.test(linkForm.discord_id.trim())) {
      setLinkError('Invalid Discord ID (must be 17–20 digits)')
      return
    }
    setLinkSaving(true)
    setLinkError(null)
    try {
      await api.linkMember(key, linkTarget.ign, { discord_id: linkForm.discord_id.trim(), discord_name: linkForm.discord_name.trim() || linkForm.discord_id.trim() })
      setLinkTarget(null)
      cache.delete(key)
      load(true)
    } catch (e: unknown) {
      setLinkError(e instanceof Error ? e.message : 'Failed to link')
    } finally {
      setLinkSaving(false)
    }
  }

  const doUnlink = async (m: GuildMember) => {
    if (!key || !confirm(`Unlink Discord account from ${m.ign}?`)) return
    try {
      await api.unlinkMember(key, m.ign)
      cache.delete(key)
      load(true)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to unlink')
    }
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

  const bottomIgns = useMemo(() => {
    const withLevel = members.filter(m => m.skyblock_level != null)
    withLevel.sort((a, b) => (a.skyblock_level ?? 0) - (b.skyblock_level ?? 0))
    return new Set(withLevel.slice(0, BOTTOM_N).map(m => m.ign))
  }, [members])

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
          {refreshing && refreshProgress && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 3 }}>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                {refreshMsg} {refreshProgress.done}/{refreshProgress.total}
              </span>
              <div style={{ width: 160, height: 4, background: 'var(--surface3)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${Math.round((refreshProgress.done / refreshProgress.total) * 100)}%`,
                  background: 'var(--accent)',
                  borderRadius: 2,
                  transition: 'width 0.3s ease',
                }} />
              </div>
            </div>
          )}
          {!refreshing && refreshMsg && <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{refreshMsg}</span>}
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
                  <th>Discord</th>
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
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {m.uuid
                          ? <img src={`https://mc-heads.net/avatar/${m.uuid}/32`} alt="" style={{ width: 32, height: 32, borderRadius: 4, flexShrink: 0 }} />
                          : <div style={{ width: 32, height: 32, borderRadius: 4, background: 'var(--surface3)', flexShrink: 0 }} />
                        }
                        <div>
                          <div style={{ fontWeight: 500 }}>
                            {m.ign}
                            {(() => {
                              const w = getWarnLevel(m, bottomIgns)
                              if (!w) return null
                              const s = WARN_STYLES[w]
                              return (
                                <span className="badge" style={{ marginLeft: 6, background: s.background, color: s.color, border: s.border }}>
                                  {s.label}
                                </span>
                              )
                            })()}
                          </div>
                          {m.uuid && <div style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-secondary)', marginTop: 2 }}>{m.uuid}</div>}
                        </div>
                      </div>
                    </td>
                    <td>
                      {m.discord_name ? (
                        <div>
                          <div style={{ fontWeight: 500 }}>{m.discord_name}</div>
                          {m.discord_id && <div style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-secondary)', marginTop: 2 }}>{m.discord_id}</div>}
                          {canManageLinks && (
                            <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                              <button className="btn btn-ghost" style={{ padding: '2px 8px', fontSize: 11 }} onClick={() => openLink(m)}>Edit</button>
                              <button className="btn btn-danger" style={{ padding: '2px 8px', fontSize: 11 }} onClick={() => doUnlink(m)}>Unlink</button>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div>
                          <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>—</span>
                          {canManageLinks && (
                            <div style={{ marginTop: 4 }}>
                              <button className="btn btn-ghost" style={{ padding: '2px 8px', fontSize: 11 }} onClick={() => openLink(m)}>Link</button>
                            </div>
                          )}
                        </div>
                      )}
                    </td>
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

      {linkTarget && (
        <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) setLinkTarget(null) }}>
          <div className="modal">
            <div className="modal-title">
              {linkTarget.discord_name ? `Edit Link — ${linkTarget.ign}` : `Link Discord — ${linkTarget.ign}`}
            </div>
            {linkError && <p style={{ color: 'var(--red)', marginBottom: 12, fontSize: 13 }}>{linkError}</p>}
            <div className="form-group">
              <label className="form-label">Discord User ID</label>
              <input
                className="form-input"
                placeholder="123456789012345678"
                value={linkForm.discord_id}
                onChange={e => setLinkForm(f => ({ ...f, discord_id: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Discord Username</label>
              <input
                className="form-input"
                placeholder="their_username"
                value={linkForm.discord_name}
                onChange={e => setLinkForm(f => ({ ...f, discord_name: e.target.value }))}
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setLinkTarget(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={saveLink} disabled={linkSaving}>
                {linkSaving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
