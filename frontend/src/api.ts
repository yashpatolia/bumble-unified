import type { BotEmoji, LevelLeaderboardData, ActivityConfig, ActivityPoint, AttentionSettings, DyeCatalog, GuildConfigData, SharedSettings, WarpoutSettings, LevelTrendPoint, ApiUsageStats, DyeDrop, DyeProfile, DyeSearchResult, GuildMember, GuildOverview, GuildStatus, Me, PanelUser } from './types'

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

/** Starts a read-only guest session (no Discord account). Stores the token; caller reloads. */
export async function startGuestSession(): Promise<void> {
  const res = await fetch('/auth/guest', { method: 'POST' })
  if (!res.ok) throw new Error('Could not start a guest session')
  const { token } = await res.json()
  localStorage.setItem('token', token)
}

export const api = {
  me: () => req<Me>('/api/me'),

  bots: () => req<Record<string, GuildStatus>>('/api/bots'),
  restartBot: (key: string) => req<{ status: string }>(`/api/bots/${key}/restart`, { method: 'POST' }),
  stopBot: (key: string) => req<{ status: string }>(`/api/bots/${key}/stop`, { method: 'POST' }),

  guildOverview: (key: string) => req<GuildOverview>(`/api/bots/${key}/overview`),
  guildMembers: (key: string) => req<{ members: GuildMember[] }>(`/api/bots/${key}/members`),

  guildActivity: (key: string, hours = 24) => req<{ points: ActivityPoint[] }>(`/api/bots/${key}/activity?hours=${hours}`),

  levelTrend: (key: string, days = 30) => req<{ points: LevelTrendPoint[] }>(`/api/bots/${key}/level-trend?days=${days}`),

  users: () => req<PanelUser[]>('/api/users'),
  createUser: (data: { discord_id: string; discord_name: string; is_admin: boolean; can_control_bots: boolean; can_fetch_api: boolean; can_manage_links: boolean; can_manage_members: boolean; can_manage_config: boolean }) =>
    req<{ status: string }>('/api/users', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (discord_id: string, data: { is_admin?: boolean; can_control_bots: boolean; can_fetch_api: boolean; can_manage_links: boolean; can_manage_members: boolean; can_manage_config: boolean }) =>
    req<{ status: string }>(`/api/users/${discord_id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteUser: (discord_id: string) =>
    req<{ status: string }>(`/api/users/${discord_id}`, { method: 'DELETE' }),

  refreshStats: (key: string) => req<{ status: string; total: number }>(`/api/bots/${key}/refresh-stats`, { method: 'POST' }),
  statsStatus: (key: string) => req<{ fetching: boolean; done: number; total: number }>(`/api/bots/${key}/stats-status`),

  apiUsage: () => req<ApiUsageStats>('/api/bots/api-usage'),

  leaderboard: (key: string, period: string) => req<{ leaderboard: { ign: string; count: number; uuid: string | null; discord_name: string | null; discord_id: string | null; discord_avatar: string | null }[] }>(`/api/bots/${key}/leaderboard?period=${period}`),

  linkMember: (key: string, ign: string, data: { discord_id: string; discord_name: string }) =>
    req<{ status: string }>(`/api/bots/${key}/members/${encodeURIComponent(ign)}/link`, { method: 'POST', body: JSON.stringify(data) }),
  unlinkMember: (key: string, ign: string) =>
    req<{ status: string }>(`/api/bots/${key}/members/${encodeURIComponent(ign)}/link`, { method: 'DELETE' }),

  kickMember: (key: string, ign: string, reason: string) =>
    req<{ status: string; ign: string }>(`/api/bots/${key}/members/${encodeURIComponent(ign)}/kick`, { method: 'POST', body: JSON.stringify({ reason }) }),
  invitePlayer: (key: string, ign: string) =>
    req<{ status: string; ign: string; message: string }>(`/api/bots/${key}/invite`, { method: 'POST', body: JSON.stringify({ ign }) }),

  excuseMember: (key: string, ign: string, data: { reason: string; until: string | null }) =>
    req<{ status: string; ign: string; reason: string | null; until: string | null }>(`/api/bots/${key}/members/${encodeURIComponent(ign)}/excuse`, { method: 'POST', body: JSON.stringify(data) }),
  removeExcuse: (key: string, ign: string) =>
    req<{ status: string }>(`/api/bots/${key}/members/${encodeURIComponent(ign)}/excuse`, { method: 'DELETE' }),
  levelLeaderboard: (key: string, days: number) => req<LevelLeaderboardData>(`/api/bots/${key}/level-leaderboard?days=${days}`),

  guildConfig: (key: string) => req<GuildConfigData>(`/api/bots/${key}/config`),
  saveGuildConfig: (key: string, data: { ranks: Record<string, number>; attention: AttentionSettings; activity: ActivityConfig; minecraft_version?: string }) =>
    req<GuildConfigData>(`/api/bots/${key}/config`, { method: 'PUT', body: JSON.stringify(data) }),

  sharedSettings: () => req<SharedSettings>('/api/settings'),
  saveSharedSettings: (data: { warpout?: WarpoutSettings; censor_words?: string[] }) =>
    req<SharedSettings>('/api/settings', { method: 'PUT', body: JSON.stringify(data) }),

  dyeCatalog: () => req<DyeCatalog>('/api/dyes/catalog'),
  saveDye: (dyeId: string, data: { dye_name: string; weight: number; hex: string; role_id: string; emoji_id: string }) =>
    req<DyeCatalog>(`/api/dyes/catalog/${encodeURIComponent(dyeId)}`, { method: 'PUT', body: JSON.stringify(data) }),
  dyeEmojis: () => req<{ emojis: BotEmoji[]; offline?: boolean }>('/api/dyes/emojis'),
  uploadDyeEmoji: (name: string, image: string) =>
    req<BotEmoji>('/api/dyes/emojis', { method: 'POST', body: JSON.stringify({ name, image }) }),
  deleteDye: (dyeId: string) => req<DyeCatalog>(`/api/dyes/catalog/${encodeURIComponent(dyeId)}`, { method: 'DELETE' }),

  myDyes: () => req<DyeProfile>('/api/dyes/me'),
  searchDyeUsers: (q: string) => req<{ results: DyeSearchResult[] }>(`/api/dyes/search?q=${encodeURIComponent(q)}`),
  userDyes: (uuid: string) => req<DyeProfile>(`/api/dyes/user/${uuid}`),
  recentDyeDrops: () => req<{ drops: DyeDrop[] }>('/api/dyes/recent'),
}
