import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import { ActivityChart } from '../components/ActivityChart'
import { LevelTrendChart } from '../components/LevelTrendChart'
import { ArrowRightIcon, CheckCircleIcon } from '../components/icons'
import { usePolling } from '../hooks/usePolling'
import { getAttention, previewNames } from '../lib/attention'
import { DEFAULT_ATTENTION, loadGuildConfig } from '../lib/guildConfig'
import { loadMembers } from '../lib/membersCache'
import type { ActivityPoint, AttentionSettings, GuildMember, GuildOverview, LevelTrendPoint } from '../types'

type BotAction = 'restart' | 'stop' | 'start' | null

export default function GuildOverviewPage() {
  const { key } = useParams<{ key: string }>()
  const { me } = useAuth()
  const canControl = me?.is_admin || me?.can_control_bots

  const [data, setData] = useState<GuildOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState<BotAction>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [members, setMembers] = useState<GuildMember[] | null>(null)
  const [activity, setActivity] = useState<ActivityPoint[] | null>(null)
  const [trendDays, setTrendDays] = useState(30)
  const [settings, setSettings] = useState<AttentionSettings>(DEFAULT_ATTENTION)
  const [trend, setTrend] = useState<LevelTrendPoint[] | null>(null)

  const fetchOverview = () => {
    if (!key) return
    api.guildOverview(key).then(setData).finally(() => setLoading(false))
  }
  usePolling(fetchOverview, 15_000, [key])
  usePolling(() => {
    if (key) api.guildActivity(key).then(r => setActivity(r.points)).catch(() => setActivity([]))
  }, 120_000, [key])

  useEffect(() => {
    if (!key) return
    setTrend(null)
    api.levelTrend(key, trendDays).then(r => setTrend(r.points)).catch(() => setTrend([]))
  }, [key, trendDays])

  useEffect(() => {
    if (!key) return
    loadGuildConfig(key).then(c => setSettings(c.attention)).catch(() => {})
  }, [key])

  useEffect(() => {
    if (!key) return
    setMembers(null)
    loadMembers(key).then(setMembers).catch(() => setMembers([]))
  }, [key])

  const act = async (action: 'restart' | 'stop' | 'start') => {
    if (!key) return
    setActing(action)
    setActionError(null)
    try {
      if (action === 'stop') {
        await api.stopBot(key)
      } else {
        await api.restartBot(key)
        setTimeout(fetchOverview, 3000)
      }
      setData(d => d ? { ...d, connected: false } : d)
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setActing(null)
    }
  }

  const attention = useMemo(() => (members ? getAttention(members, settings).filter(i => i.id !== 'excused') : []), [members, settings])
  const stats = useMemo(() => {
    if (!members) return null
    const online = members.filter(m => m.online).length
    // Bot accounts sit in the roster but are not real players, so they stay out of the average.
    const levels = members.filter(m => !m.is_bot).map(m => m.skyblock_level).filter((l): l is number => l != null)
    const avg = levels.length ? levels.reduce((a, b) => a + b, 0) / levels.length : 0
    const linked = members.filter(m => m.discord_name).length
    const messages = members.reduce((a, m) => a + (m.messages_90d ?? 0), 0)
    const climbers = [...members].filter(m => (m.level_gain_90d ?? 0) > 0).sort((a, b) => (b.level_gain_90d ?? 0) - (a.level_gain_90d ?? 0)).slice(0, 5)
    return { online, avg, linked, messages, total: members.length, climbers }
  }, [members])

  if (loading) return <p className="text-muted">Loading...</p>
  if (!data || !key) return <p className="text-muted">Failed to load overview.</p>

  const chat = [...(data.recent_chat ?? [])].reverse()

  return (
    <div>
      <div className="crumb reveal">{data.short_name} / Overview</div>
      <div className="page-head reveal" style={{ '--i': 1 } as React.CSSProperties}>
        <h1 className="page-title">
          {data.name}
          <span className={`badge ${data.connected ? 'badge-on' : 'badge-danger'}`} style={{ marginLeft: 12, verticalAlign: 'middle', fontFamily: 'var(--font-body)', fontSize: 12.5 }}>
            <span className={`dot ${data.connected ? 'on' : 'off'}`} />
            {data.connected ? 'Connected' : 'Offline'}
          </span>
        </h1>
        {canControl && (
          <div className="head-actions">
            {actionError && <span className="error-text" style={{ margin: 0 }}>{actionError}</span>}
            <button className="btn" disabled={!!acting} onClick={() => act('restart')}>{acting === 'restart' ? 'Restarting...' : 'Restart bot'}</button>
            {data.connected ? (
              <button className="btn btn-danger" disabled={!!acting} onClick={() => act('stop')}>{acting === 'stop' ? 'Stopping...' : 'Stop bot'}</button>
            ) : (
              <button className="btn btn-primary" disabled={!!acting} onClick={() => act('start')}>{acting === 'start' ? 'Starting...' : 'Start bot'}</button>
            )}
          </div>
        )}
      </div>

      <div className="kpis">
        {[
          { label: 'Members', value: stats ? stats.total : (data.member_count || '...'), sub: stats ? `${stats.online} online right now` : 'Loading roster' },
          { label: 'Online now', value: stats ? stats.online : '...', sub: stats && stats.total ? `${Math.round((stats.online / stats.total) * 100)}% of the guild` : '' },
          { label: 'Average level', value: stats ? stats.avg.toFixed(0) : '...', sub: 'Skyblock level, bots excluded' },
          { label: 'Discord linked', value: stats ? `${stats.linked}/${stats.total}` : '...', sub: stats ? `${stats.total - stats.linked} not linked` : '' },
        ].map((k, i) => (
          <div key={k.label} className="card kpi reveal" style={{ '--i': 2 + i } as React.CSSProperties}>
            <div className="k-label">{k.label}</div>
            <div className="k-value num">{k.value}</div>
            <div className="k-sub">{k.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <div className="stack">
          <div className="card reveal" style={{ '--i': 6 } as React.CSSProperties}>
            <div className="card-head">
              <span className="card-title">Activity today</span>
              <span className="card-sub">Members online, by hour</span>
            </div>
            {activity == null ? <div className="chart-empty">Loading...</div> : <ActivityChart points={activity} />}
          </div>

          <div className="card reveal" style={{ '--i': 7 } as React.CSSProperties}>
            <div className="card-head">
              <span className="card-title">Average level</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {trend && trend.length > 1 && (() => {
                  const delta = trend[trend.length - 1].avg - trend[0].avg
                  return (
                    <span className="card-sub">
                      <b className="num" style={{ color: 'var(--text)' }}>{trend[trend.length - 1].avg.toFixed(1)}</b>{' '}
                      <span className={delta >= 0 ? 'gain-up' : 'gain-down'}>{delta >= 0 ? '+' : ''}{delta.toFixed(1)}</span> in {trendDays} days
                    </span>
                  )
                })()}
                <span className="tabs">
                  {[30, 90].map(d => (
                    <button key={d} className={`tab${trendDays === d ? ' active' : ''}`} onClick={() => setTrendDays(d)}>{d}d</button>
                  ))}
                </span>
              </span>
            </div>
            {trend == null ? <div className="chart-empty">Loading...</div> : <LevelTrendChart points={trend} days={trendDays} />}
          </div>

          <div className="card reveal" style={{ '--i': 8 } as React.CSSProperties}>
            <div className="card-head">
              <span className="card-title">Guild chat</span>
              <span className="card-sub">Last {chat.length} messages</span>
            </div>
            <div className="feed">
              {chat.length === 0 ? (
                <div className="empty">No messages yet.</div>
              ) : chat.map((msg, i) => (
                <div className="chat-line" key={i}>
                  <span className="chat-time">{msg.time}</span>
                  <span className="chat-player">{msg.player}</span>
                  <span className="chat-msg">{msg.message}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="stack">
          <div className="card reveal" style={{ '--i': 6 } as React.CSSProperties}>
            <div className="card-head">
              <span className="card-title">Needs attention</span>
              <span className="card-sub">{members ? `${attention.length} ${attention.length === 1 ? 'item' : 'items'}` : ''}</span>
            </div>
            {members == null ? (
              <div className="empty">Checking the roster...</div>
            ) : attention.length === 0 ? (
              <div className="allclear"><CheckCircleIcon width={22} height={22} />Nothing needs your attention.</div>
            ) : (
              <div style={{ paddingBottom: 6 }}>
                {attention.map(item => (
                  <Link key={item.id} to={`/guilds/${key}/members?filter=${item.id}`} className={`attn ${item.tone}`}>
                    <span className="attn-count num">{item.members.length}</span>
                    <span className="attn-body">
                      <div className="attn-label">{item.label}</div>
                      <div className="attn-who">{previewNames(item.members)}</div>
                    </span>
                    <ArrowRightIcon className="attn-go" width={16} height={16} />
                  </Link>
                ))}
              </div>
            )}
          </div>

          {stats && stats.climbers.length > 0 && (
            <div className="card reveal" style={{ '--i': 7 } as React.CSSProperties}>
              <div className="card-head">
                <span className="card-title">Top climbers</span>
                <span className="card-sub">Level gained, 90 days</span>
              </div>
              <div style={{ paddingBottom: 8 }}>
                {stats.climbers.map(m => (
                  <div className="attn" key={m.ign} style={{ cursor: 'default' }}>
                    {m.uuid ? <img src={`https://mc-heads.net/avatar/${m.uuid}/32`} alt="" width={32} height={32} style={{ borderRadius: 8 }} /> : <span className="avatar-fallback" style={{ borderRadius: 8 }}>{m.ign[0]}</span>}
                    <span className="attn-body"><div className="attn-label">{m.ign}</div><div className="attn-who">{m.rank}</div></span>
                    <span className="gain-up num">+{(m.level_gain_90d ?? 0).toFixed(1)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
