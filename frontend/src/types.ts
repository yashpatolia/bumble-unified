export interface Me {
  discord_id: string
  discord_name: string
  is_admin: boolean
  can_view_logs: boolean
  can_control_bots: boolean
  avatar_url: string
}

export interface Bot {
  key: string
  name: string
  short_name: string
  username: string
  connected: boolean
}

export interface PanelUser {
  discord_id: string
  discord_name: string
  is_admin: boolean
  can_view_logs: boolean
  can_control_bots: boolean
}

export interface LogRecord {
  type?: 'ping'
  time?: string
  level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  message?: string
  source?: string
}
