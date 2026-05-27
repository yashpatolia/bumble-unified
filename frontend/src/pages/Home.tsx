import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import type { GuildStatus } from '../types'

type BotAction = 'restart' | 'stop' | 'start' | null

export default function Home() {
  const { me, logout } = useAuth()
  const navigate = useNavigate()
  const [bots, setBots] = useState<Record<string, GuildStatus>>({})
  const [acting, setActing] = useState<Record<string, BotAction>>({})
  const [error, setError] = useState<string | null>(null)

  const canControl = me?.is_admin || me?.can_control_bots

  const fetchBots = () => {
    if (!canControl) return
    api.bots()
      .then(setBots)
      .catch(() => {})
  }

  useEffect(() => {
    fetchBots()
    if (!canControl) return
    const id = setInterval(fetchBots, 10_000)
    return () => clearInterval(id)
  }, [])

  const act = async (key: string, action: 'restart' | 'stop' | 'start') => {
    setActing(a => ({ ...a, [key]: action }))
    setError(null)
    try {
      if (action === 'stop') {
        await api.stopBot(key)
        setBots(b => ({ ...b, [key]: { ...b[key], connected: false } }))
      } else {
        await api.restartBot(key)
        setBots(b => ({ ...b, [key]: { ...b[key], connected: false } }))
        setTimeout(fetchBots, 3000)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setActing(a => ({ ...a, [key]: null }))
    }
  }

  const handleLogout = () => { logout(); navigate('/login') }

  const guildList = Object.values(bots).length > 0
    ? Object.values(bots)
    : [{ key: 'bk', name: 'Bumble Kindergarten', short_name: 'BK', username: '—', connected: false }, { key: 'bu', name: 'Bumble University', short_name: 'BU', username: '—', connected: false }]

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
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/users')}>Admin</button>
          )}
          <button className="btn btn-ghost btn-sm" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <div className="home-body">
        <div className="home-title">Welcome back{me?.discord_name ? `, ${me.discord_name}` : ''}</div>
        <div className="home-sub">Select a guild to view its overview.</div>

        {error && <p style={{ color: 'var(--red)', marginBottom: 16 }}>{error}</p>}

        <div className="guild-cards">
          {guildList.map(bot => (
            <Link key={bot.key} className="guild-card" to={`/guilds/${bot.key}`}>
              <div className="guild-card-header">
                <div>
                  <div className="guild-card-name">{bot.name}</div>
                  <div className="guild-card-tag">[{bot.short_name}] · {bot.username}</div>
                </div>
                {canControl && (
                  <div className="guild-card-status">
                    <span className={`status-dot ${bot.connected ? 'online' : 'offline'}`} />
                    {bot.connected ? 'Online' : 'Offline'}
                  </div>
                )}
              </div>

              {canControl && (
                <div className="guild-card-actions" onClick={e => e.preventDefault()}>
                  {bot.connected ? (
                    <button className="btn btn-danger btn-sm" disabled={!!acting[bot.key]} onClick={() => act(bot.key, 'stop')}>
                      {acting[bot.key] === 'stop' ? 'Stopping...' : 'Stop'}
                    </button>
                  ) : (
                    <button className="btn btn-primary btn-sm" disabled={!!acting[bot.key]} onClick={() => act(bot.key, 'start')}>
                      {acting[bot.key] === 'start' ? 'Starting...' : 'Start'}
                    </button>
                  )}
                  <button className="btn btn-ghost btn-sm" disabled={!!acting[bot.key]} onClick={() => act(bot.key, 'restart')}>
                    {acting[bot.key] === 'restart' ? 'Restarting...' : 'Restart'}
                  </button>
                </div>
              )}

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
