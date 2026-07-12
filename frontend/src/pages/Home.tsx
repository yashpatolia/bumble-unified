import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import type { GuildStatus } from '../types'

const FALLBACK: GuildStatus[] = [
  { key: 'bk', name: 'Bumble Kindergarten', short_name: 'BK', username: '—', connected: false },
  { key: 'bu', name: 'Bumble University',   short_name: 'BU', username: '—', connected: false },
]

export default function Home() {
  const { me } = useAuth()
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
    <div>
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
  )
}
