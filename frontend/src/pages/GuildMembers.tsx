import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import { DiscordIdentityCell, PlayerIdentityCell } from '../components/IdentityCell'
import { CalendarIcon, ChevronRightIcon, LinkIcon, PencilIcon, SearchIcon, UnlinkIcon, UserMinusIcon } from '../components/icons'
import { Modal } from '../components/Modal'
import { getAttention } from '../lib/attention'
import { DEFAULT_ACTIVITY, tierColor, TIER_NAMES, tierIndex } from '../lib/activity'
import { DEFAULT_ATTENTION, loadGuildConfig } from '../lib/guildConfig'
import { clearCachedMembers, getCachedMembers, loadMembers, setCachedMembers } from '../lib/membersCache'
import { formatRelativeTime } from '../lib/time'
import { isValidDiscordId } from '../lib/validators'
import type { ActivityConfig, AttentionSettings, GuildMember } from '../types'

type SortKey = 'ign' | 'rank' | 'level' | 'last_login' | 'status' | 'messages_90d' | 'messages_total'
type SortDir = 'asc' | 'desc'

const BASE_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'online', label: 'Online' },
  { id: 'offline', label: 'Offline' },
]

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** 2026-11-15 becomes "Nov 15". */
function shortDate(iso: string): string {
  const [, m, d] = iso.split('-').map(Number)
  return `${MONTHS[m - 1]} ${d}`
}

function formatLastLogin(ts: number | null): string {
  if (!ts) return 'N/A'
  return formatRelativeTime(Date.now() - ts, { maxTier: 'years' })
}

function formatFetchedAt(ts: number | null): string {
  if (!ts) return 'Never'
  // stats_fetched_at is a Unix seconds timestamp
  return formatRelativeTime(Date.now() - ts * 1000, { justNowUnderMins: 2 })
}

export default function GuildMembers() {
  const { key } = useParams<{ key: string }>()
  const [params, setParams] = useSearchParams()
  const filter = params.get('filter') ?? 'all'
  const { me } = useAuth()
  const canFetch = me?.can_fetch_api || me?.is_admin || me?.is_owner
  const canManageLinks = me?.can_manage_links || me?.is_admin || me?.is_owner
  const canManageMembers = me?.can_manage_members || me?.is_admin || me?.is_owner

  const [members, setMembers] = useState<GuildMember[]>(key ? getCachedMembers(key) ?? [] : [])
  const [loading, setLoading] = useState(!(key && getCachedMembers(key)))
  const [error, setError] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>('status')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [search, setSearch] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null)
  const [refreshProgress, setRefreshProgress] = useState<{ done: number; total: number } | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [linkTarget, setLinkTarget] = useState<GuildMember | null>(null)
  const [linkForm, setLinkForm] = useState({ discord_id: '', discord_name: '' })
  const [linkSaving, setLinkSaving] = useState(false)
  const [linkError, setLinkError] = useState<string | null>(null)

  // Kick / invite (in-game actions run by the bot)
  const [kickTarget, setKickTarget] = useState<GuildMember | null>(null)
  const [kickReason, setKickReason] = useState('')
  const [kickBusy, setKickBusy] = useState(false)
  const [kickError, setKickError] = useState<string | null>(null)
  const [showInvite, setShowInvite] = useState(false)
  const [inviteIgn, setInviteIgn] = useState('')
  const [inviteBusy, setInviteBusy] = useState(false)
  const [inviteError, setInviteError] = useState<string | null>(null)
  const [inviteResult, setInviteResult] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [excuseTarget, setExcuseTarget] = useState<GuildMember | null>(null)
  const [excuseReason, setExcuseReason] = useState('')
  const [excuseUntil, setExcuseUntil] = useState('')
  const [excuseBusy, setExcuseBusy] = useState(false)
  const [excuseError, setExcuseError] = useState<string | null>(null)
  const [settings, setSettings] = useState<AttentionSettings>(DEFAULT_ATTENTION)
  const [activity, setActivity] = useState<ActivityConfig>(DEFAULT_ACTIVITY)

  const load = (force = false) => {
    if (!key) return
    setLoading(true)
    setError(null)
    loadMembers(key, force)
      .then(setMembers)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load members'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [key])
  useEffect(() => {
    if (key) loadGuildConfig(key).then(c => { setSettings(c.attention); setActivity(c.activity) }).catch(() => {})
  }, [key])
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
          setRefreshMsg('Done. Refreshing list...')
          clearCachedMembers(k)
          load(true)
          setTimeout(() => setRefreshMsg(null), 3000)
        }
      } catch { /* keep polling */ }
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
    if (sortKey === k) setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    else {
      setSortKey(k)
      setSortDir(k === 'last_login' || k === 'level' || k === 'status' || k === 'messages_90d' || k === 'messages_total' ? 'desc' : 'asc')
    }
  }
  const arrow = (k: SortKey) => sortKey === k
    ? <ChevronRightIcon width={12} height={12} style={{ marginLeft: 4, verticalAlign: -1, transform: `rotate(${sortDir === 'asc' ? -90 : 90}deg)` }} />
    : null

  const openLink = (m: GuildMember) => {
    setLinkTarget(m)
    setLinkForm({ discord_id: m.discord_id ?? '', discord_name: m.discord_name ?? '' })
    setLinkError(null)
  }

  const patchMember = (ign: string, patch: Partial<GuildMember>) => {
    setMembers(prev => {
      const next = prev.map(m => (m.ign === ign ? { ...m, ...patch } : m))
      if (key) setCachedMembers(key, next)
      return next
    })
  }

  const saveLink = async () => {
    if (!key || !linkTarget) return
    if (!isValidDiscordId(linkForm.discord_id.trim())) {
      setLinkError('Invalid Discord ID (must be 17 to 20 digits)')
      return
    }
    setLinkSaving(true)
    setLinkError(null)
    const discordId = linkForm.discord_id.trim()
    const discordName = linkForm.discord_name.trim() || discordId
    try {
      await api.linkMember(key, linkTarget.ign, { discord_id: discordId, discord_name: discordName })
      patchMember(linkTarget.ign, { discord_id: discordId, discord_name: discordName, discord_avatar: linkTarget.discord_avatar ?? null })
      setLinkTarget(null)
    } catch (e: unknown) {
      setLinkError(e instanceof Error ? e.message : 'Failed to link')
    } finally {
      setLinkSaving(false)
    }
  }

  const confirmKick = async () => {
    if (!key || !kickTarget) return
    setKickBusy(true)
    setKickError(null)
    try {
      await api.kickMember(key, kickTarget.ign, kickReason.trim())
      const next = members.filter(m => m.ign !== kickTarget.ign)
      setMembers(next)
      setCachedMembers(key, next)
      setNotice(`Kick command sent for ${kickTarget.ign}.`)
      setTimeout(() => setNotice(null), 5000)
      setKickTarget(null)
    } catch (e: unknown) {
      setKickError(e instanceof Error ? e.message : 'Kick failed')
    } finally {
      setKickBusy(false)
    }
  }

  const sendInvite = async () => {
    if (!key || !inviteIgn.trim()) return
    setInviteBusy(true)
    setInviteError(null)
    setInviteResult(null)
    try {
      const res = await api.invitePlayer(key, inviteIgn.trim())
      setInviteResult(res.message)
      setInviteIgn('')
    } catch (e: unknown) {
      setInviteError(e instanceof Error ? e.message : 'Invite failed')
    } finally {
      setInviteBusy(false)
    }
  }

  const closeInvite = () => { setShowInvite(false); setInviteIgn(''); setInviteError(null); setInviteResult(null) }

  const openExcuse = (m: GuildMember) => {
    setExcuseTarget(m)
    setExcuseReason(m.excused?.reason ?? '')
    setExcuseUntil(m.excused?.until ?? '')
    setExcuseError(null)
  }

  const saveExcuse = async () => {
    if (!key || !excuseTarget) return
    setExcuseBusy(true)
    setExcuseError(null)
    try {
      const res = await api.excuseMember(key, excuseTarget.ign, { reason: excuseReason.trim(), until: excuseUntil || null })
      patchMember(excuseTarget.ign, { excused: { reason: res.reason, until: res.until, by: me?.discord_name ?? null } })
      setExcuseTarget(null)
    } catch (e: unknown) {
      setExcuseError(e instanceof Error ? e.message : 'Could not save the excuse')
    } finally {
      setExcuseBusy(false)
    }
  }

  const removeExcuse = async (m: GuildMember) => {
    if (!key) return
    try {
      await api.removeExcuse(key, m.ign)
      patchMember(m.ign, { excused: null })
      setExcuseTarget(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Could not remove the excuse')
    }
  }

  const doUnlink = async (m: GuildMember) => {
    if (!key || !confirm(`Unlink Discord account from ${m.ign}?`)) return
    try {
      await api.unlinkMember(key, m.ign)
      patchMember(m.ign, { discord_id: null, discord_name: null, discord_avatar: null })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to unlink')
    }
  }

  const attention = useMemo(() => getAttention(members, settings), [members, settings])
  const attentionByMember = useMemo(() => {
    const map = new Map<string, { label: string; tone: string }>()
    for (const item of attention) {
      if (item.id === 'unlinked' || item.id === 'stale' || item.id === 'excused') continue
      for (const m of item.members) if (!map.has(m.ign)) map.set(m.ign, { label: item.short, tone: item.tone })
    }
    return map
  }, [attention])

  const filters = [...BASE_FILTERS, ...attention.map(a => ({ id: a.id, label: a.label.split(' (')[0] }))]
  const counts: Record<string, number> = {
    all: members.length,
    online: members.filter(m => m.online).length,
    offline: members.filter(m => !m.online).length,
  }
  for (const a of attention) counts[a.id] = a.members.length

  const visible = useMemo(() => {
    let list = members
    if (filter === 'online') list = list.filter(m => m.online)
    else if (filter === 'offline') list = list.filter(m => !m.online)
    else if (filter !== 'all') {
      const set = new Set(attention.find(a => a.id === filter)?.members.map(m => m.ign) ?? [])
      list = list.filter(m => set.has(m.ign))
    }
    const q = search.trim().toLowerCase()
    if (q) list = list.filter(m => m.ign.toLowerCase().includes(q) || (m.discord_name ?? '').toLowerCase().includes(q))
    return [...list].sort((a, b) => {
      let cmp = 0
      if (sortKey === 'ign') cmp = a.ign.localeCompare(b.ign)
      else if (sortKey === 'rank') cmp = a.rank.localeCompare(b.rank)
      else if (sortKey === 'level') cmp = (a.skyblock_level ?? -1) - (b.skyblock_level ?? -1)
      else if (sortKey === 'last_login') cmp = (a.last_login ?? 0) - (b.last_login ?? 0)
      else if (sortKey === 'status') cmp = (a.online ? 1 : 0) - (b.online ? 1 : 0)
      else if (sortKey === 'messages_90d') cmp = (a.messages_90d ?? 0) - (b.messages_90d ?? 0)
      else if (sortKey === 'messages_total') cmp = (a.messages_total ?? 0) - (b.messages_total ?? 0)
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [members, filter, search, sortKey, sortDir, attention])

  const setFilter = (id: string) => setParams(id === 'all' ? {} : { filter: id }, { replace: true })

  return (
    <div>
      <div className="crumb reveal">{key?.toUpperCase()} / Members</div>
      <div className="page-head reveal" style={{ '--i': 1 } as React.CSSProperties}>
        <h1 className="page-title">
          Members
          {members.length > 0 && <small>{counts.online} online, {members.length} total</small>}
        </h1>
        <div className="head-actions">
          {refreshing && refreshProgress && (
            <div style={{ width: 170 }}>
              <div className="card-sub">{refreshMsg} {refreshProgress.done}/{refreshProgress.total}</div>
              <div className="meter" style={{ marginTop: 4 }}><i style={{ width: `${Math.round((refreshProgress.done / refreshProgress.total) * 100)}%` }} /></div>
            </div>
          )}
          {!refreshing && refreshMsg && <span className="card-sub">{refreshMsg}</span>}
          {canManageMembers && <button className="btn btn-primary" onClick={() => setShowInvite(true)}>Invite player</button>}
          {canFetch && <button className="btn" onClick={refreshStats} disabled={refreshing}>{refreshing ? 'Fetching...' : 'Refresh stats'}</button>}
          <button className="btn" onClick={() => load(true)} disabled={loading}>{loading ? 'Loading...' : 'Reload list'}</button>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}
      {notice && <p className="badge badge-on" style={{ marginBottom: 12 }}>{notice}</p>}

      <div className="card reveal" style={{ '--i': 2 } as React.CSSProperties}>
        <div className="card-pad" style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="chips">
            {filters.map(f => (
              <button key={f.id} className={`chip${filter === f.id ? ' active' : ''}`} onClick={() => setFilter(f.id)}>
                {f.label}<span className="n">{counts[f.id] ?? 0}</span>
              </button>
            ))}
          </div>
          <div style={{ position: 'relative', width: 240, maxWidth: '100%' }}>
            <SearchIcon width={16} height={16} style={{ position: 'absolute', left: 11, top: 10, color: 'var(--text-2)' }} />
            <input className="form-input" style={{ paddingLeft: 34 }} placeholder="Search name or Discord" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
        </div>

        <div className="table-wrap">
          {loading && members.length === 0 ? (
            <p className="empty">Fetching the guild list from Minecraft...</p>
          ) : visible.length === 0 ? (
            <p className="empty">No members match this view.</p>
          ) : (
            <table className="compact">
              <thead>
                <tr>
                  <th>
                    <span className="sortable" style={{ cursor: 'pointer' }} onClick={() => handleSort('ign')}>Player{arrow('ign')}</span>
                    <span style={{ opacity: 0.5 }}> / </span>
                    <span className="sortable" style={{ cursor: 'pointer' }} onClick={() => handleSort('rank')}>Rank{arrow('rank')}</span>
                  </th>
                  <th>Discord</th>
                  <th className="sortable" onClick={() => handleSort('level')}>Level{arrow('level')}</th>
                  <th className="sortable" onClick={() => handleSort('last_login')} title="Last login">Seen{arrow('last_login')}</th>
                  <th className="sortable" onClick={() => handleSort('status')}>Status{arrow('status')}</th>
                  <th className="sortable" onClick={() => handleSort('messages_90d')} style={{ textAlign: 'right' }}>Messages{arrow('messages_90d')}<div style={{ fontWeight: 500, fontSize: 11 }}>last 90 days</div></th>
                  <th className="sortable" onClick={() => handleSort('messages_total')} style={{ textAlign: 'right' }}>Messages{arrow('messages_total')}<div style={{ fontWeight: 500, fontSize: 11 }}>all time</div></th>
                  <th title="When this member's stats were last refreshed">Updated</th>
                  {canManageMembers && <th style={{ width: 1 }}></th>}
                </tr>
              </thead>
              <tbody>
                {visible.map(m => {
                  const flag = attentionByMember.get(m.ign)
                  return (
                    <tr key={m.ign}>
                      <td>
                        <PlayerIdentityCell
                          uuid={m.uuid}
                          ign={m.ign}
                          sub={m.rank}
                          badge={<>
                            {flag && <span className={`badge badge-${flag.tone === 'danger' ? 'danger' : 'warn'}`}>{flag.label}</span>}
                            {m.excused && <span className="badge" title={[m.excused.reason, m.excused.until ? `until ${m.excused.until}` : 'until removed'].filter(Boolean).join(', ')}>Excused{m.excused.until ? `, ${shortDate(m.excused.until)}` : ''}</span>}
                          </>}
                        />
                      </td>
                      <td>
                        <DiscordIdentityCell
                          name={m.discord_name}
                          avatar={m.discord_avatar}
                          actions={canManageLinks && (
                            <span style={{ display: 'flex', gap: 4 }}>
                              <button className="icon-btn sm" onClick={() => openLink(m)} title="Edit Discord link" aria-label={`Edit Discord link for ${m.ign}`}><PencilIcon width={14} height={14} /></button>
                              <button className="icon-btn sm danger" onClick={() => doUnlink(m)} title="Unlink Discord" aria-label={`Unlink Discord from ${m.ign}`}><UnlinkIcon width={14} height={14} /></button>
                            </span>
                          )}
                          emptyActions={canManageLinks && <button className="icon-btn sm" onClick={() => openLink(m)} title="Link a Discord account" aria-label={`Link Discord to ${m.ign}`}><LinkIcon width={14} height={14} /></button>}
                        />
                      </td>
                      <td className="num" style={{ whiteSpace: 'nowrap' }} title={m.stats_fetched_at ? `Stats fetched ${new Date(m.stats_fetched_at * 1000).toLocaleString()}` : undefined}>
                        {m.skyblock_level != null ? m.skyblock_level.toFixed(1) : 'N/A'}
                        {m.level_gain_90d != null && (
                          <div className={m.level_gain_90d >= 0 ? 'gain-up' : 'gain-down'} style={{ fontSize: 12 }}>
                            {m.level_gain_90d >= 0 ? '+' : ''}{m.level_gain_90d.toFixed(1)}
                            {m.level_gain_days != null && m.level_gain_days < 90 ? ` in ${m.level_gain_days}d` : ''}
                          </div>
                        )}
                      </td>
                      <td className="text-muted" style={{ whiteSpace: 'nowrap' }}>{formatLastLogin(m.last_login)}</td>
                      <td>{m.online ? <span className="badge badge-on">Online</span> : <span className="badge badge-off">Offline</span>}</td>
                      <td className="num" style={{ textAlign: 'right', fontWeight: 600, color: tierColor(m.messages_90d ?? 0, activity.d90) }} title={TIER_NAMES[tierIndex(m.messages_90d ?? 0, activity.d90)]}>{(m.messages_90d ?? 0).toLocaleString()}</td>
                      <td className="num" style={{ textAlign: 'right', fontWeight: 600, color: tierColor(m.messages_total ?? 0, activity.total) }} title={TIER_NAMES[tierIndex(m.messages_total ?? 0, activity.total)]}>{(m.messages_total ?? 0).toLocaleString()}</td>
                      <td className="text-muted" style={{ whiteSpace: 'nowrap', fontSize: 12.5 }}>{formatFetchedAt(m.stats_fetched_at)}</td>
                      {canManageMembers && (
                        <td>
                          <span style={{ display: 'flex', gap: 4 }}>
                            <button className={`icon-btn sm${m.excused ? ' active' : ''}`} onClick={() => openExcuse(m)} title={m.excused ? 'Edit or remove excuse' : 'Excuse from inactivity warnings'} aria-label={`${m.excused ? 'Edit excuse for' : 'Excuse'} ${m.ign}`}><CalendarIcon width={14} height={14} /></button>
                            <button className="icon-btn sm danger" onClick={() => { setKickTarget(m); setKickReason(''); setKickError(null) }} title="Kick from guild" aria-label={`Kick ${m.ign}`}><UserMinusIcon width={14} height={14} /></button>
                          </span>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {kickTarget && (
        <Modal
          title={`Kick ${kickTarget.ign}?`}
          onClose={() => setKickTarget(null)}
          error={kickError}
          actions={<>
            <button className="btn btn-ghost" onClick={() => setKickTarget(null)}>Cancel</button>
            <button className="btn btn-danger" onClick={confirmKick} disabled={kickBusy}>{kickBusy ? 'Sending...' : 'Kick from guild'}</button>
          </>}
        >
          {kickTarget.excused && (
            <p className="badge badge-warn" style={{ marginBottom: 12, whiteSpace: 'normal' }}>
              {kickTarget.ign} is excused{kickTarget.excused.reason ? `: ${kickTarget.excused.reason}` : ''}{kickTarget.excused.until ? ` (until ${kickTarget.excused.until})` : ''}.
            </p>
          )}
          <p className="card-sub" style={{ marginBottom: 14 }}>
            The bot will run <span className="mono">/guild kick {kickTarget.ign} {kickReason.trim() || 'Removed via panel'}</span> in game right away. This is logged to the guild logs channel with your name.
          </p>
          <div className="form-group">
            <label className="form-label">Reason</label>
            <input className="form-input" placeholder="Inactive for 60+ days" maxLength={100} value={kickReason} onChange={e => setKickReason(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') confirmKick() }} autoFocus />
            <div className="chips" style={{ marginTop: 8 }}>
              {['Inactive', 'Inactive for 60+ days', 'Does not meet requirements', 'Requested to leave'].map(r => (
                <button key={r} type="button" className="chip" onClick={() => setKickReason(r)}>{r}</button>
              ))}
            </div>
          </div>
        </Modal>
      )}

      {excuseTarget && (
        <Modal
          title={excuseTarget.excused ? `Excuse for ${excuseTarget.ign}` : `Excuse ${excuseTarget.ign}`}
          onClose={() => setExcuseTarget(null)}
          error={excuseError}
          actions={<>
            {excuseTarget.excused && <button className="btn btn-ghost" style={{ marginRight: 'auto' }} onClick={() => removeExcuse(excuseTarget)}>Remove excuse</button>}
            <button className="btn btn-ghost" onClick={() => setExcuseTarget(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={saveExcuse} disabled={excuseBusy}>{excuseBusy ? 'Saving...' : 'Save'}</button>
          </>}
        >
          <p className="card-sub" style={{ marginBottom: 14 }}>
            Excused members are left out of the inactivity warnings (low activity, inactive, kick risk). Nothing happens in game.
          </p>
          <div className="form-group">
            <label className="form-label">Reason (staff only, optional)</label>
            <input className="form-input" placeholder="On vacation, exams, alt account..." maxLength={200} value={excuseReason} onChange={e => setExcuseReason(e.target.value)} autoFocus />
          </div>
          <div className="form-group">
            <label className="form-label">Excused until (optional)</label>
            <input className="form-input" type="date" value={excuseUntil} min={new Date().toISOString().slice(0, 10)} onChange={e => setExcuseUntil(e.target.value)} />
            <div className="card-sub" style={{ marginTop: 4 }}>Leave empty to excuse them until you remove it.</div>
          </div>
        </Modal>
      )}

      {showInvite && (
        <Modal
          title="Invite a player"
          onClose={closeInvite}
          error={inviteError}
          actions={<>
            <button className="btn btn-ghost" onClick={closeInvite}>{inviteResult ? 'Done' : 'Cancel'}</button>
            <button className="btn btn-primary" onClick={sendInvite} disabled={inviteBusy || !inviteIgn.trim()}>{inviteBusy ? 'Sending...' : 'Send invite'}</button>
          </>}
        >
          <div className="form-group">
            <label className="form-label">Minecraft username</label>
            <input className="form-input" placeholder="Their in-game name" maxLength={16} value={inviteIgn} onChange={e => setInviteIgn(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') sendInvite() }} autoFocus />
          </div>
          {inviteResult && <p className="badge badge-on" style={{ whiteSpace: 'normal' }}>{inviteResult}</p>}
        </Modal>
      )}

      {linkTarget && (
        <Modal
          title={linkTarget.discord_name ? `Edit link for ${linkTarget.ign}` : `Link Discord to ${linkTarget.ign}`}
          onClose={() => setLinkTarget(null)}
          error={linkError}
          actions={<>
            <button className="btn btn-ghost" onClick={() => setLinkTarget(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={saveLink} disabled={linkSaving}>{linkSaving ? 'Saving...' : 'Save'}</button>
          </>}
        >
          <div className="form-group">
            <label className="form-label">Discord user ID</label>
            <input className="form-input" placeholder="123456789012345678" value={linkForm.discord_id} onChange={e => setLinkForm(f => ({ ...f, discord_id: e.target.value }))} />
          </div>
          <div className="form-group">
            <label className="form-label">Discord username</label>
            <input className="form-input" placeholder="their_username" value={linkForm.discord_name} onChange={e => setLinkForm(f => ({ ...f, discord_name: e.target.value }))} />
          </div>
        </Modal>
      )}
    </div>
  )
}
