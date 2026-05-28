import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import type { GuildOverview } from '../types'

const EVENT_COLORS: Record<string, string> = {
  join: 'join', leave: 'leave', kick: 'kick',
  mute: 'mute', unmute: 'unmute', promote: 'promote', demote: 'demote',
}

type BotAction = 'restart' | 'stop' | 'start' | null

export default function GuildOverviewPage() {
  const { key } = useParams<{ key: string }>()
  const { me } = useAuth()
  const canControl = me?.is_admin || me?.can_control_bots

  const [data, setData] = useState<GuildOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState<BotAction>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const fetchOverview = () => {
    if (!key) return
    api.guildOverview(key).then(setData)
  }

  useEffect(() => {
    if (!key) return
    api.guildOverview(key)
      .then(setData)
      .finally(() => setLoading(false))
    const id = setInterval(fetchOverview, 15_000)
    return () => clearInterval(id)
  }, [key])

  const act = async (action: 'restart' | 'stop' | 'start') => {
    if (!key) return
    setActing(action)
    setActionError(null)
    try {
      if (action === 'stop') {
        await api.stopBot(key)
        setData(d => d ? { ...d, connected: false } : d)
      } else {
        await api.restartBot(key)
        setData(d => d ? { ...d, connected: false } : d)
        setTimeout(fetchOverview, 3000)
      }
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setActing(null)
    }
  }

  if (loading) return <p className="text-muted">Loading...</p>
  if (!data) return <p className="text-muted">Failed to load overview.</p>

  return (
    <div>
      <div className="header-row" style={{ marginBottom: 20 }}>
        <div className="page-title" style={{ marginBottom: 0 }}>{data.name}</div>
        {canControl && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {actionError && <span style={{ fontSize: 12, color: 'var(--red)' }}>{actionError}</span>}
            {data.connected ? (
              <button className="btn btn-danger" disabled={!!acting} onClick={() => act('stop')}>
                {acting === 'stop' ? 'Stopping…' : 'Stop'}
              </button>
            ) : (
              <button className="btn btn-primary" disabled={!!acting} onClick={() => act('start')}>
                {acting === 'start' ? 'Starting…' : 'Start'}
              </button>
            )}
            <button className="btn btn-ghost" disabled={!!acting} onClick={() => act('restart')}>
              {acting === 'restart' ? 'Restarting…' : 'Restart'}
            </button>
          </div>
        )}
      </div>

      <div className="overview-stat-row">
        <div className="stat-card">
          <div className="stat-label">Status</div>
          <div className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 16 }}>
            <span className={`status-dot ${data.connected ? 'online' : 'offline'}`} />
            {data.connected ? 'Online' : 'Offline'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Bot Account</div>
          <div className="stat-value" style={{ fontSize: 16 }}>{data.username}</div>
        </div>
        {data.member_count > 0 && (
          <div className="stat-card">
            <div className="stat-label">Members</div>
            <div className="stat-value">{data.member_count}</div>
          </div>
        )}
      </div>

      <div className="overview-grid">
        <div className="feed-card">
          <div className="feed-header">
            <span>Recent Chat</span>
            <span className="text-muted" style={{ fontSize: 12 }}>last 50 messages</span>
          </div>
          <div className="feed-body">
            {data.recent_chat.length === 0 ? (
              <div className="feed-empty">No messages yet.</div>
            ) : (
              data.recent_chat.map((msg, i) => (
                <div className="chat-line" key={i}>
                  <span className="chat-time">{msg.time}</span>
                  <img src={`https://mc-heads.net/avatar/${msg.player}/24`} alt="" style={{ width: 24, height: 24, borderRadius: 3, flexShrink: 0 }} />
                  <span className="chat-player">{msg.player}</span>
                  <span className="chat-msg">{msg.message}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="feed-card">
          <div className="feed-header">
            <span>Recent Events</span>
            <span className="text-muted" style={{ fontSize: 12 }}>joins, leaves, kicks</span>
          </div>
          <div className="feed-body">
            {data.recent_events.length === 0 ? (
              <div className="feed-empty">No events yet.</div>
            ) : (
              data.recent_events.map((ev, i) => (
                <div className="event-line" key={i}>
                  <span className="event-time">{ev.time}</span>
                  <span className={`event-dot ${EVENT_COLORS[ev.type] ?? 'default'}`} />
                  <span className="event-msg">{ev.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
