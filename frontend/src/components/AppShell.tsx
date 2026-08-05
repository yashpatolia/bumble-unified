import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import { usePolling } from '../hooks/usePolling'
import type { GuildStatus } from '../types'

const GUILDS: { key: string; name: string }[] = [
  { key: 'bk', name: 'Bumble Kindergarten' },
  { key: 'bu', name: 'Bumble University' },
]

const navClass = ({ isActive }: { isActive: boolean }) =>
  'sidebar-link' + (isActive ? ' active' : '')

export default function AppShell() {
  const { me, logout } = useAuth()
  const navigate = useNavigate()
  const [bots, setBots] = useState<Record<string, GuildStatus>>({})

  usePolling(() => { api.bots().then(setBots).catch(() => {}) }, 15_000)

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link to="/" className="sidebar-brand">
          <span className="hex-mark" />
          Bumble
        </Link>

        <nav className="sidebar-nav">
          <NavLink to="/" end className={navClass}>Home</NavLink>

          {GUILDS.map(g => {
            const status = bots[g.key]
            return (
              <div className="sidebar-group" key={g.key}>
                <div className="sidebar-group-label">
                  <span className={`status-dot ${status?.connected ? 'online' : 'offline'}`} />
                  {g.name}
                </div>
                <div className="sidebar-subnav">
                  <NavLink to={`/guilds/${g.key}`} end className={navClass}>Overview</NavLink>
                  <NavLink to={`/guilds/${g.key}/members`} className={navClass}>Members</NavLink>
                  <NavLink to={`/guilds/${g.key}/leaderboard`} className={navClass}>Leaderboard</NavLink>
                </div>
              </div>
            )
          })}

          <div className="sidebar-group">
            <NavLink to="/dyes" className={navClass}>Dyes</NavLink>
            {me?.is_owner && <NavLink to="/admin" className={navClass}>Admin</NavLink>}
            {me?.is_admin && <NavLink to="/users" className={navClass}>Users</NavLink>}
          </div>
        </nav>

        <div className="sidebar-footer">
          {me?.avatar_url
            ? <img src={me.avatar_url} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
            : <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--surface3)' }} />
          }
          <span className="sidebar-user-name">{me?.discord_name}</span>
          <button className="btn btn-ghost btn-sm" style={{ marginLeft: 'auto' }} onClick={handleLogout}>Logout</button>
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
