import { useNavigate } from 'react-router-dom'
import { useAuth } from '../App'

const PLANNED_EVENTS = [
  {
    slug: 'guild-bingo',
    name: 'Guild Bingo',
    icon: '🎯',
    guilds: ['BK', 'BU'],
    description:
      'Each member receives a bingo card filled with Skyblock tasks of varying difficulty. Complete goals to mark your squares and compete for the best score across the guild.',
  },
]

export default function Events() {
  const { me, logout } = useAuth()
  const navigate = useNavigate()

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
        <div className="home-title">Events</div>
        <div className="home-sub">Guild-wide challenges and competitions — run for BK, BU, or both guilds simultaneously.</div>

        <div style={{ marginBottom: 40 }}>
          <div className="events-section-label">Active Events</div>
          <div className="card events-empty-state">
            <div className="events-empty-icon">📋</div>
            <div className="events-empty-title">No active events</div>
            <div className="events-empty-sub">Check back soon — events will appear here when they go live.</div>
          </div>
        </div>

        <div>
          <div className="events-section-label">Coming Soon</div>
          <div className="guild-cards">
            {PLANNED_EVENTS.map(event => (
              <div key={event.slug} className="event-preview-card">
                <div className="event-preview-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span className="event-preview-icon">{event.icon}</span>
                    <div>
                      <div className="event-preview-name">{event.name}</div>
                      <div style={{ display: 'flex', gap: 4, marginTop: 5 }}>
                        {event.guilds.map(g => (
                          <span key={g} className="badge badge-warn" style={{ fontSize: 10 }}>{g}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <span className="badge badge-user">Coming Soon</span>
                </div>
                <p className="event-preview-desc">{event.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
