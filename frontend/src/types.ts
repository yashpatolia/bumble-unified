export interface Me {
  discord_id: string
  discord_name: string
  is_admin: boolean
  can_control_bots: boolean
  can_fetch_api: boolean
  can_manage_links: boolean
  can_manage_events: boolean
  avatar_url: string
  is_owner: boolean
}

export interface GuildStatus {
  key: string
  name: string
  short_name: string
  username: string
  connected: boolean
}

export interface ChatMessage {
  time: string
  player: string
  message: string
}

export interface GuildEvent {
  time: string
  type: 'join' | 'leave' | 'kick' | 'mute' | 'unmute' | 'promote' | 'demote' | string
  message: string
}

export interface GuildOverview {
  key: string
  name: string
  short_name: string
  username: string
  connected: boolean
  member_count: number
  recent_chat: ChatMessage[]
  recent_events: GuildEvent[]
}

export interface GuildMember {
  rank: string
  ign: string
  uuid: string | null
  discord_name: string | null
  discord_id: string | null
  discord_avatar: string | null
  online: boolean
  skyblock_level: number | null
  last_login: number | null
  stats_fetched_at: number | null
}

export interface ApiUsageStats {
  local: {
    last_minute: number
    last_5min: number
    last_hour: number
    today: number
  }
  hypixel: {
    queries_in_past_minute?: number
    total_queries?: number
    limit?: number
  }
  rate_limit: {
    requests: number
    window_minutes: number
  }
}

export interface PanelUser {
  discord_id: string
  discord_name: string
  is_admin: boolean
  can_control_bots: boolean
  can_fetch_api: boolean
  can_manage_links: boolean
  can_manage_events: boolean
  is_owner: boolean
}

export type EventMode =
  | 'individual'
  | 'team'
  | 'combined_shared'
  | 'combined_versus'
  | 'combined_individual'

export type EventStatus = 'draft' | 'active' | 'ended'

export interface BingoEvent {
  id: number
  slug: string
  type: string
  name: string
  mode: EventMode
  guilds: string[]
  status: EventStatus
  starts_at: string | null
  ends_at: string | null
  created_at: string
}

export interface BingoTask {
  id: number
  event_id: number
  position: number
  name: string
  description: string
  task_type: string
  target: Record<string, unknown>
  difficulty: 'easy' | 'medium' | 'hard'
}

export interface BingoCardEntry extends BingoTask {
  baseline: number | null
  current_val: number | null
  completed: boolean
  completed_at: string | null
  last_updated: string | null
  progress: number | null
}

export interface BingoLeaderboardEntry {
  uuid: string
  ign: string | null
  completed_count: number
  blackout: boolean
  discord_name: string | null
  discord_avatar: string | null
  guild_key: string | null
  last_updated: string | null
}

export interface LogRecord {
  type?: 'ping'
  time?: string
  level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  message?: string
  source?: string
}
