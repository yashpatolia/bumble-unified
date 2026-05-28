import { createContext, useContext, useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { api } from './api'
import type { Me } from './types'
import Login from './pages/Login'
import Home from './pages/Home'
import GuildLayout from './pages/GuildLayout'
import GuildOverview from './pages/GuildOverview'
import GuildMembers from './pages/GuildMembers'
import GuildLeaderboard from './pages/GuildLeaderboard'
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
      <Route path="/" element={me ? <Home /> : <Navigate to="/login" replace />} />
      <Route path="/guilds/:key" element={<Protected><GuildLayout /></Protected>}>
        <Route index element={<GuildOverview />} />
        <Route path="members" element={<GuildMembers />} />
        <Route path="leaderboard" element={<GuildLeaderboard />} />
        <Route path="logs" element={<Logs />} />
      </Route>
      <Route path="/users" element={<Protected adminOnly><Users /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
