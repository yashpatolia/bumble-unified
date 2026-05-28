export interface Me {
  discord_id: string
  discord_name: string
  is_admin: boolean
  can_view_logs: boolean
  can_control_bots: boolean
  can_fetch_api: boolean
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
  online: boolean
  skyblock_level: number | null
  last_login: number | null
}

export interface PanelUser {
  discord_id: string
  discord_name: string
  is_admin: boolean
  can_view_logs: boolean
  can_control_bots: boolean
  can_fetch_api: boolean
  is_owner: boolean
}

export interface LogRecord {
  type?: 'ping'
  time?: string
  level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  message?: string
  source?: string
}
