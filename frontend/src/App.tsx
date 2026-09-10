import { createContext, useContext, useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { api } from './api'
import type { Me } from './types'
import AppShell from './components/AppShell'
import Login from './pages/Login'
import Home from './pages/Home'
import GuildOverview from './pages/GuildOverview'
import GuildMembers from './pages/GuildMembers'
import GuildLeaderboard from './pages/GuildLeaderboard'
import Admin from './pages/Admin'
import Users from './pages/Users'
import Dyes from './pages/Dyes'

interface AuthCtx {
  me: Me | null
  loading: boolean
  logout: () => void
}

const Auth = createContext<AuthCtx>({ me: null, loading: true, logout: () => {} })
export const useAuth = () => useContext(Auth)

// Dev-only escape hatch so the UI can be worked on without a running backend/OAuth
// setup. `import.meta.env.DEV` is compiled to `false` in `npm run build`, so this
// branch (and the bypass button in Login.tsx) is dead-code-eliminated from prod.
const DEV_BYPASS_KEY = 'dev_bypass'
const DEV_ME: Me = {
  discord_id: '0', discord_name: 'Dev User', is_admin: true, can_control_bots: true,
  can_fetch_api: true, can_manage_links: true, avatar_url: '', is_owner: true,
}

function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (import.meta.env.DEV && localStorage.getItem(DEV_BYPASS_KEY)) {
      setMe(DEV_ME)
      setLoading(false)
      return
    }
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
    localStorage.removeItem(DEV_BYPASS_KEY)
    setMe(null)
  }

  return <Auth.Provider value={{ me, loading, logout }}>{children}</Auth.Provider>
}

function Protected({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
  const { me, loading } = useAuth()
  if (loading) return null
  if (!me) return <Navigate to="/login" replace />
  if (adminOnly && !me.is_admin) return <Navigate to="/" replace />
  return <>{children}</>
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
      <Route path="/login" element={me ? <Navigate to="/" replace /> : <Login />} />
      <Route element={<Protected><AppShell /></Protected>}>
        <Route path="/" element={<Home />} />
        <Route path="/guilds/:key" element={<GuildOverview />} />
        <Route path="/guilds/:key/members" element={<GuildMembers />} />
        <Route path="/guilds/:key/leaderboard" element={<GuildLeaderboard />} />
        <Route path="/dyes" element={<Dyes />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/users" element={<Protected adminOnly><Users /></Protected>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
