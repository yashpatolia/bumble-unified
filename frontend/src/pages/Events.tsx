import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import type { BingoEvent } from '../types'

const MODE_LABELS: Record<string, string> = {
  individual: 'Individual',
  team: 'Team',
  combined_shared: 'Combined — Shared Card',
  combined_versus: 'BK vs BU',
  combined_individual: 'Combined — Individual',
}

const GUILD_LABELS: Record<string, string> = { bk: 'BK', bu: 'BU' }

function EventCard({ event }: { event: BingoEvent }) {
  return (
    <Link className="guild-card" to={`/events/${event.slug}`}>
      <div className="guild-card-header">
        <div>
          <div className="guild-card-name" style={{ fontSize: 18 }}>{event.name}</div>
          <div style={{ display: 'flex', gap: 5, marginTop: 6, flexWrap: 'wrap' }}>
            {event.guilds.map(g => (
              <span key={g} className="badge badge-warn" style={{ fontSize: 10 }}>{GUILD_LABELS[g] ?? g.toUpperCase()}</span>
            ))}
            <span className="badge badge-user" style={{ fontSize: 10 }}>{MODE_LABELS[event.mode] ?? event.mode}</span>
          </div>
        </div>
        {event.status === 'active' && (
          <span className="badge badge-on" style={{ whiteSpace: 'nowrap', marginTop: 3 }}>Active</span>
        )}
        {event.status === 'draft' && (
          <span className="badge badge-warn" style={{ whiteSpace: 'nowrap', marginTop: 3 }}>Draft</span>
        )}
        {event.status === 'ended' && (
          <span className="badge badge-off" style={{ whiteSpace: 'nowrap', marginTop: 3 }}>Ended</span>
        )}
      </div>
      <div className="guild-card-footer">
        <span className="guild-enter">
          {event.status === 'draft' ? 'Edit Event →' : 'View Event →'}
        </span>
      </div>
    </Link>
  )
}

export default function Events() {
  const { me, logout } = useAuth()
  const navigate = useNavigate()
  const isManager = me?.can_manage_events || me?.is_admin || false
  const [events, setEvents] = useState<BingoEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listEvents()
      .then(r => setEvents(r.events))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const active = events.filter(e => e.status === 'active')
  const draft = events.filter(e => e.status === 'draft')
  const ended = events.filter(e => e.status === 'ended')

  return (
    <div className="home-page">
      <header className="home-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span className="guild-header-back" onClick={() => navigate('/')}>← All Guilds</span>
          <span className="guild-header-sep">/</span>
          <div className="home-logo" style={{ fontSize: 14, fontWeight: 600 }}>Events</div>
        </div>
        <div className="home-user">
          {me?.avatar_url && (
            <img src={me.avatar_url} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
          )}
          <span>{me?.discord_name}</span>
          {me?.is_owner && (
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/users')}>Admin</button>
          )}
          <button className="btn btn-ghost btn-sm" onClick={() => { logout(); navigate('/login') }}>Logout</button>
        </div>
      </header>

      <div className="home-body">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
          <div className="home-title" style={{ marginBottom: 0 }}>Events</div>
          {isManager && (
            <button className="btn btn-primary" onClick={() => navigate('/events/new')}>+ New Event</button>
          )}
        </div>
        <div className="home-sub">Guild-wide challenges and competitions for BK, BU, or both guilds.</div>

        {loading ? (
          <p className="empty">Loading...</p>
        ) : !isManager && active.length === 0 ? (
          /* Non-managers see coming soon when nothing is active */
          <>
            <div className="events-section-label">Active Events</div>
            <div className="card events-empty-state">
              <div className="events-empty-icon">📋</div>
              <div className="events-empty-title">No active events right now</div>
              <div className="events-empty-sub">Check back soon — events will appear here when they go live.</div>
            </div>
            <div style={{ marginTop: 32 }}>
              <div className="events-section-label">Coming Soon</div>
              <div className="guild-cards">
                <div className="event-preview-card">
                  <div className="event-preview-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span className="event-preview-icon">🎯</span>
                      <div>
                        <div className="event-preview-name">Guild Bingo</div>
                        <div style={{ display: 'flex', gap: 4, marginTop: 5 }}>
                          <span className="badge badge-warn" style={{ fontSize: 10 }}>BK</span>
                          <span className="badge badge-warn" style={{ fontSize: 10 }}>BU</span>
                        </div>
                      </div>
                    </div>
                    <span className="badge badge-user">Coming Soon</span>
                  </div>
                  <p className="event-preview-desc">
                    Each member receives a bingo card with Skyblock tasks of varying difficulty.
                    Complete goals to mark your squares and compete for a full blackout.
                  </p>
                </div>
              </div>
            </div>
          </>
        ) : (
          /* Managers (or when there are active events) see full event lists */
          <>
            {(active.length > 0 || isManager) && (
              <div style={{ marginBottom: 32 }}>
                <div className="events-section-label">Active Events</div>
                {active.length === 0 ? (
                  <div className="card events-empty-state" style={{ padding: '32px 24px' }}>
                    <div className="events-empty-title">No active events</div>
                    <div className="events-empty-sub">Activate a draft event to make it visible to everyone.</div>
                  </div>
                ) : (
                  <div className="guild-cards">
                    {active.map(e => <EventCard key={e.slug} event={e} />)}
                  </div>
                )}
              </div>
            )}

            {isManager && draft.length > 0 && (
              <div style={{ marginBottom: 32 }}>
                <div className="events-section-label">Drafts</div>
                <div className="guild-cards">
                  {draft.map(e => <EventCard key={e.slug} event={e} />)}
                </div>
              </div>
            )}

            {isManager && ended.length > 0 && (
              <div>
                <div className="events-section-label">Ended</div>
                <div className="guild-cards">
                  {ended.map(e => <EventCard key={e.slug} event={e} />)}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
