import { createContext, useContext, useEffect, useState } from 'react'
import { BrowserRouter, NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api } from './api'
import type { Me } from './types'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Logs from './pages/Logs'
import Users from './pages/Users'

interface AuthCtx {
  me: Me | null
  loading: boolean
  logout: () => void
}

const Auth = createContext<AuthCtx>({ me: null, loading: true, logout: () => {} })
export const useAuth = () => useContext(Auth)

function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Pick up token from OAuth redirect (?token=...)
    const params = new URLSearchParams(window.location.search)
    const t = params.get('token')
    if (t) {
      localStorage.setItem('token', t)
      window.history.replaceState({}, '', window.location.pathname)
    }

    if (!localStorage.getItem('token')) {
      setLoading(false)
      return
    }
    api.me()
      .then(setMe)
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false))
  }, [])

  const logout = () => {
    localStorage.removeItem('token')
    setMe(null)
  }

  return <Auth.Provider value={{ me, loading, logout }}>{children}</Auth.Provider>
}

function Protected({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
  const { me, loading } = useAuth()
  if (loading) return null
  if (!me) return <Navigate to="/" replace />
  if (adminOnly && !me.is_admin) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

function Layout() {
  const { me, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-logo">🐝 Bumble Panel</div>
        <nav className="sidebar-nav">
          <NavLink className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')} to="/dashboard">
            Dashboard
          </NavLink>
          {(me?.is_admin || me?.can_view_logs) && (
            <NavLink className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')} to="/logs">
              Logs
            </NavLink>
          )}
          {me?.is_admin && (
            <NavLink className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')} to="/users">
              Users
            </NavLink>
          )}
        </nav>
        <div className="sidebar-user">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
            {me?.avatar_url && (
              <img src={me.avatar_url} alt="" style={{ width: 28, height: 28, borderRadius: '50%', flexShrink: 0 }} />
            )}
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{me?.discord_name}</span>
          </div>
          <button className="btn btn-ghost" style={{ padding: '4px 10px', fontSize: 12, flexShrink: 0 }} onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/logs" element={<Protected><Logs /></Protected>} />
          <Route path="/users" element={<Protected adminOnly><Users /></Protected>} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </BrowserRouter>
  )
}

function AppRouter() {
  const { me, loading } = useAuth()
  if (loading) return null
  return (
    <Routes>
      <Route path="/" element={me ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route path="/*" element={me ? <Layout /> : <Navigate to="/" replace />} />
    </Routes>
  )
}
