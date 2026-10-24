import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import { usePolling } from '../hooks/usePolling'
import { DropletIcon, GearIcon, LogoutIcon, MenuIcon, ShieldIcon, TrophyIcon, UsersIcon, BotIcon, SlidersIcon } from './icons'
import { ThemeToggle } from './ThemeToggle'
import type { GuildStatus } from '../types'

const GUILDS: { key: string; short: string; name: string }[] = [
  { key: 'bk', short: 'BK', name: 'Kindergarten' },
  { key: 'bu', short: 'BU', name: 'University' },
]

const navClass = ({ isActive }: { isActive: boolean }) => 'nav-link' + (isActive ? ' active' : '')
const LAST_GUILD_KEY = 'last_guild'

function currentGuildKey(pathname: string): string | null {
  const m = pathname.match(/^\/guilds\/([^/]+)/)
  return m ? m[1] : null
}

export default function AppShell() {
  const { me, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [bots, setBots] = useState<Record<string, GuildStatus>>({})
  const [navOpen, setNavOpen] = useState(false)

  usePolling(() => { api.bots().then(setBots).catch(() => {}) }, 15_000)
  useEffect(() => { setNavOpen(false) }, [pathname])

  const routeGuild = currentGuildKey(pathname)
  // The switcher remembers the last guild you looked at, so Dyes/Admin pages keep your place.
  useEffect(() => { if (routeGuild) try { localStorage.setItem(LAST_GUILD_KEY, routeGuild) } catch { /* ignore */ } }, [routeGuild])
  let remembered: string | null = null
  try { remembered = localStorage.getItem(LAST_GUILD_KEY) } catch { /* ignore */ }
  const guild = routeGuild ?? (GUILDS.some(g => g.key === remembered) ? remembered! : 'bk')
  const status = bots[guild]

  const handleLogout = () => { logout(); navigate('/') }

  return (
    <div className={`shell${navOpen ? ' nav-open' : ''}`}>
      <aside className="sidebar">
        <Link to="/" className="brand">Bumble</Link>

        <div className="guild-switch">
          {GUILDS.map(g => (
            <Link key={g.key} to={`/guilds/${g.key}`} className={g.key === guild ? 'active' : ''}>
              <span className={`dot ${bots[g.key]?.connected ? 'on' : bots[g.key] ? 'off' : ''}`} />
              {g.short}
            </Link>
          ))}
        </div>

        <nav className="nav">
          <div className="nav-label">{GUILDS.find(g => g.key === guild)?.name}</div>
          <NavLink to={`/guilds/${guild}`} end className={navClass}><BotIcon />Overview</NavLink>
          <NavLink to={`/guilds/${guild}/members`} className={navClass}><UsersIcon />Members</NavLink>
          <NavLink to={`/guilds/${guild}/leaderboard`} className={navClass}><TrophyIcon />Leaderboard</NavLink>
          <NavLink to={`/guilds/${guild}/config`} className={navClass}><SlidersIcon />Config</NavLink>
          <div className="nav-label" style={{ marginTop: 10 }}>Tools</div>
          <NavLink to="/dyes" className={navClass}><DropletIcon />Dyes</NavLink>
          <NavLink to="/admin" className={navClass}><GearIcon />Admin</NavLink>
          <NavLink to="/users" className={navClass}><ShieldIcon />Users</NavLink>
        </nav>

        <div className="sidebar-bottom">
          {me?.is_guest && <div className="badge badge-off" style={{ justifyContent: 'center' }}>Guest, read only</div>}
          <div className="health">
            <div className="health-row">
              <span className="label">Bot</span>
              <b style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <span className={`dot ${status?.connected ? 'on' : status ? 'off' : ''}`} />
                {status ? (status.connected ? 'Connected' : 'Offline') : 'Checking'}
              </b>
            </div>
          </div>
          <div className="user-row">
            {me?.avatar_url
              ? <img className="avatar" src={me.avatar_url} alt="" width={30} height={30} />
              : <div className="avatar-fallback">{me?.discord_name?.[0]?.toUpperCase() ?? '?'}</div>}
            <span className="name">{me?.discord_name}</span>
            <ThemeToggle />
            <button className="icon-btn" onClick={handleLogout} title={me?.is_guest ? 'Leave guest mode' : 'Log out'} aria-label={me?.is_guest ? 'Leave guest mode' : 'Log out'}><LogoutIcon /></button>
          </div>
          {me?.is_guest && (
            <a href="/auth/discord" className="btn btn-sm" style={{ justifyContent: 'center' }}>Sign in with Discord</a>
          )}
        </div>
      </aside>

      <div style={{ minWidth: 0 }}>
        <div className="mobile-bar">
          <button className="icon-btn" onClick={() => setNavOpen(o => !o)} aria-label="Menu"><MenuIcon /></button>
          <span className="brand" style={{ padding: 0 }}>Bumble</span>
          <ThemeToggle />
        </div>
        <main className="main">
          <Outlet key={pathname} />
        </main>
      </div>
    </div>
  )
}
