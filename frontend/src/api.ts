import type { GuildMember, GuildOverview, GuildStatus, Me, PanelUser } from './types'

function token(): string | null {
  return localStorage.getItem('token')
}

function authHeaders(): HeadersInit {
  const t = token()
  return {
    'Content-Type': 'application/json',
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
  }
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, { ...init, headers: authHeaders() })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: 'Request failed' }))
    const detail = body.detail
    throw new Error(typeof detail === 'string' ? detail : 'Request failed')
  }
  return res.json() as Promise<T>
}

export const api = {
  me: () => req<Me>('/api/me'),

  bots: () => req<Record<string, GuildStatus>>('/api/bots'),
  restartBot: (key: string) => req<{ status: string }>(`/api/bots/${key}/restart`, { method: 'POST' }),
  stopBot: (key: string) => req<{ status: string }>(`/api/bots/${key}/stop`, { method: 'POST' }),

  guildOverview: (key: string) => req<GuildOverview>(`/api/bots/${key}/overview`),
  guildMembers: (key: string) => req<{ members: GuildMember[] }>(`/api/bots/${key}/members`),

  users: () => req<PanelUser[]>('/api/users'),
  createUser: (data: { discord_id: string; discord_name: string; is_admin: boolean; can_view_logs: boolean; can_control_bots: boolean; can_fetch_api: boolean; can_manage_links: boolean }) =>
    req<{ status: string }>('/api/users', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (discord_id: string, data: { can_view_logs: boolean; can_control_bots: boolean; can_fetch_api: boolean; can_manage_links: boolean }) =>
    req<{ status: string }>(`/api/users/${discord_id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteUser: (discord_id: string) =>
    req<{ status: string }>(`/api/users/${discord_id}`, { method: 'DELETE' }),

  refreshStats: (key: string) => req<{ status: string; total: number }>(`/api/bots/${key}/refresh-stats`, { method: 'POST' }),
  statsStatus: (key: string) => req<{ fetching: boolean; done: number; total: number }>(`/api/bots/${key}/stats-status`),

  leaderboard: (key: string, period: string) => req<{ leaderboard: { ign: string; count: number; uuid: string | null; discord_name: string | null; discord_id: string | null; discord_avatar: string | null }[] }>(`/api/bots/${key}/leaderboard?period=${period}`),

  linkMember: (key: string, ign: string, data: { discord_id: string; discord_name: string }) =>
    req<{ status: string }>(`/api/bots/${key}/members/${encodeURIComponent(ign)}/link`, { method: 'POST', body: JSON.stringify(data) }),
  unlinkMember: (key: string, ign: string) =>
    req<{ status: string }>(`/api/bots/${key}/members/${encodeURIComponent(ign)}/link`, { method: 'DELETE' }),
}

export function wsLogsUrl(): string {
  const t = token() ?? ''
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  return `${proto}://${host}/ws/logs?token=${encodeURIComponent(t)}`
}
