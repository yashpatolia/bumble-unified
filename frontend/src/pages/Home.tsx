import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import { ArrowRightIcon } from '../components/icons'
import { usePolling } from '../hooks/usePolling'
import type { GuildStatus } from '../types'

const FALLBACK: GuildStatus[] = [
  { key: 'bk', name: 'Bumble Kindergarten', short_name: 'BK', username: '', connected: false },
  { key: 'bu', name: 'Bumble University', short_name: 'BU', username: '', connected: false },
]

export default function Home() {
  const { me } = useAuth()
  const [bots, setBots] = useState<GuildStatus[]>([])
  usePolling(() => { api.bots().then(d => setBots(Object.values(d))).catch(() => {}) }, 15_000)
  const guilds = bots.length > 0 ? bots : FALLBACK

  return (
    <div>
      <div className="page-head reveal">
        <h1 className="page-title">{me?.is_guest ? 'Welcome, guest' : `Welcome back${me?.discord_name ? `, ${me.discord_name}` : ''}`}</h1>
      </div>
      <div className="card-sub reveal" style={{ '--i': 1 } as React.CSSProperties}>Pick a guild to see its overview.</div>
      <div className="section-label reveal" style={{ '--i': 2 } as React.CSSProperties}>Guilds</div>
      <div className="guild-cards">
        {guilds.map((bot, i) => (
          <Link key={bot.key} className="card guild-card reveal" style={{ '--i': 3 + i } as React.CSSProperties} to={`/guilds/${bot.key}`}>
            <span className={`badge ${bot.connected ? 'badge-on' : 'badge-off'}`}>
              <span className={`dot ${bot.connected ? 'on' : ''}`} />
              {bot.connected ? 'Connected' : 'Offline'}
            </span>
            <div className="g-name">{bot.name}</div>
            <div className="g-foot">Open overview <ArrowRightIcon width={16} height={16} /></div>
          </Link>
        ))}
      </div>
    </div>
  )
}
