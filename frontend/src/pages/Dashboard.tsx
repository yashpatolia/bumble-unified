import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../App'
import type { Bot } from '../types'

type BotAction = 'restart' | 'stop' | 'start' | null

export default function Dashboard() {
  const { me } = useAuth()
  const [bots, setBots] = useState<Record<string, Bot>>({})
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState<Record<string, BotAction>>({})
  const [error, setError] = useState<string | null>(null)

  const canControl = me?.is_admin || me?.can_control_bots

  const fetchBots = () => {
    if (!canControl) { setLoading(false); return }
    api.bots()
      .then(setBots)
      .catch(() => setError('Failed to load bot status'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchBots()
    const id = setInterval(fetchBots, 10_000)
    return () => clearInterval(id)
  }, [])

  const act = async (key: string, action: 'restart' | 'stop' | 'start') => {
    setActing(a => ({ ...a, [key]: action }))
    setError(null)
    try {
      if (action === 'restart') {
        await api.restartBot(key)
        setBots(b => ({ ...b, [key]: { ...b[key], connected: false } }))
        setTimeout(fetchBots, 3000)
      } else if (action === 'stop') {
        await api.stopBot(key)
        setBots(b => ({ ...b, [key]: { ...b[key], connected: false } }))
      } else {
        await api.restartBot(key)
        setTimeout(fetchBots, 3000)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setActing(a => ({ ...a, [key]: null }))
    }
  }

  if (!canControl) {
    return (
      <div>
        <div className="page-title">Dashboard</div>
        <div className="card">
          <p style={{ color: 'var(--muted)' }}>Welcome, {me?.discord_name}. Contact an admin for additional access.</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-title">Dashboard</div>
      {error && <p style={{ color: 'var(--red)', marginBottom: 16 }}>{error}</p>}
      {loading ? (
        <p style={{ color: 'var(--muted)' }}>Loading...</p>
      ) : (
        <div className="card-grid">
          {Object.values(bots).map(bot => (
            <div className="card bot-card" key={bot.key}>
              <div className="bot-card-header">
                <div>
                  <div className="bot-name">{bot.name}</div>
                  <div className="bot-username">{bot.username}</div>
                </div>
                <div className="status-label">
                  <span className={`status-dot ${bot.connected ? 'online' : 'offline'}`} />
                  {bot.connected ? 'Online' : 'Offline'}
                </div>
              </div>
              {(me?.is_admin || me?.can_control_bots) && (
                <div className="bot-actions">
                  {bot.connected ? (
                    <button
                      className="btn btn-danger"
                      disabled={!!acting[bot.key]}
                      onClick={() => act(bot.key, 'stop')}
                    >
                      {acting[bot.key] === 'stop' ? 'Stopping...' : 'Stop'}
                    </button>
                  ) : (
                    <button
                      className="btn btn-primary"
                      disabled={!!acting[bot.key]}
                      onClick={() => act(bot.key, 'start')}
                    >
                      {acting[bot.key] === 'start' ? 'Starting...' : 'Start'}
                    </button>
                  )}
                  <button
                    className="btn btn-ghost"
                    disabled={!!acting[bot.key]}
                    onClick={() => act(bot.key, 'restart')}
                  >
                    {acting[bot.key] === 'restart' ? 'Restarting...' : 'Restart'}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
