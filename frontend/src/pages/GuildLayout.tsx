import { NavLink, Outlet, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../App'

export default function GuildLayout() {
  const { key } = useParams<{ key: string }>()
  const { me, logout } = useAuth()
  const navigate = useNavigate()

  const guildName = key === 'bk' ? 'Bumble Kindergarten' : key === 'bu' ? 'Bumble University' : key?.toUpperCase()

  const handleLogout = () => { logout(); navigate('/login') }

  const navClass = ({ isActive }: { isActive: boolean }) =>
    'topnav-link' + (isActive ? ' active' : '')

  return (
    <div className="guild-layout">
      <header className="guild-header">
        <div className="guild-header-left">
          <span className="guild-header-back" onClick={() => navigate('/')}>← All Guilds</span>
          <span className="guild-header-sep">/</span>
          <span className="guild-header-name">{guildName}</span>
        </div>

        <nav className="topnav">
          <NavLink className={navClass} to={`/guilds/${key}`} end>Overview</NavLink>
          <NavLink className={navClass} to={`/guilds/${key}/members`}>Members</NavLink>
          <NavLink className={navClass} to={`/guilds/${key}/leaderboard`}>Leaderboard</NavLink>
          <NavLink className={navClass} to={`/guilds/${key}/events`}>Events</NavLink>
        </nav>

        <div className="guild-header-user">
          {me?.avatar_url && (
            <img src={me.avatar_url} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
          )}
          <span>{me?.discord_name}</span>
          {me?.is_owner && (
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/admin')}>Admin</button>
          )}
          <button className="btn btn-ghost btn-sm" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <main className="guild-main">
        <Outlet />
      </main>
    </div>
  )
}
