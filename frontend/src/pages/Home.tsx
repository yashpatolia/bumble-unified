import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import type { GuildStatus } from '../types'

const FALLBACK: GuildStatus[] = [
  { key: 'bk', name: 'Bumble Kindergarten', short_name: 'BK', username: '—', connected: false },
  { key: 'bu', name: 'Bumble University',   short_name: 'BU', username: '—', connected: false },
]

export default function Home() {
  const { me, logout } = useAuth()
  const navigate = useNavigate()
  const [bots, setBots] = useState<GuildStatus[]>([])

  useEffect(() => {
    api.bots()
      .then(data => setBots(Object.values(data)))
      .catch(() => {})
    const id = setInterval(() =>
      api.bots().then(data => setBots(Object.values(data))).catch(() => {}), 15_000)
    return () => clearInterval(id)
  }, [])

  const guildList = bots.length > 0 ? bots : FALLBACK

  return (
    <div className="home-page">
      <header className="home-header">
        <div className="home-logo">Bumble</div>
        <div className="home-user">
          {me?.avatar_url && (
            <img src={me.avatar_url} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
          )}
          <span>{me?.discord_name}</span>
          {me?.is_owner && (
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/admin')}>Admin</button>
          )}
          <button className="btn btn-ghost btn-sm" onClick={() => { logout(); navigate('/login') }}>Logout</button>
        </div>
      </header>

      <div className="home-body">
        <div className="home-title">Welcome back{me?.discord_name ? `, ${me.discord_name}` : ''}</div>
        <div className="home-sub">Select a guild to view its overview.</div>

        <div className="events-section-label">Guilds</div>
        <div className="guild-cards">
          {guildList.map(bot => (
            <Link key={bot.key} className="guild-card" to={`/guilds/${bot.key}`}>
              <div className="guild-card-header">
                <div>
                  <div className="guild-card-name">{bot.name}</div>
                  <div className="guild-card-tag">{bot.username}</div>
                </div>
                <div className="guild-card-status">
                  <span className={`status-dot ${bot.connected ? 'online' : 'offline'}`} />
                  {bot.connected ? 'Online' : 'Offline'}
                </div>
              </div>
              <div className="guild-card-footer">
                <span className="guild-enter">View Guild →</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
