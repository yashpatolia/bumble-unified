export interface Me {
  discord_id: string
  discord_name: string
  is_admin: boolean
  can_control_bots: boolean
  can_fetch_api: boolean
  can_manage_links: boolean
  can_manage_members?: boolean
  can_manage_config?: boolean
  avatar_url: string
  is_owner: boolean
  is_guest?: boolean
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

export interface GuildOverview {
  key: string
  name: string
  short_name: string
  username: string
  connected: boolean
  member_count: number
  recent_chat: ChatMessage[]
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
  messages_90d: number
  messages_total: number
  is_bot?: boolean
  excused?: { reason: string | null; until: string | null; by: string | null } | null
  level_gain_90d: number | null
  level_gain_days: number | null
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
  can_manage_members?: boolean
  can_manage_config?: boolean
  is_owner: boolean
}

export interface Dye {
  dye_id: string
  dye_name: string
  hex: string
  weight: number
  odds: string
  unlocked: boolean
}

export interface DyeProfile {
  linked: boolean
  uuid?: string
  ign?: string
  discord_name?: string | null
  discord_avatar?: string | null
  dyes?: Dye[]
}

export interface DyeSearchResult {
  uuid: string
  ign: string
  discord_id: string | null
  discord_name: string | null
  discord_avatar: string | null
  unlocked_count: number
}

export interface DyeDrop {
  dye_id: string
  dye_name: string
  hex: string
  unlocked_at: string
  uuid: string
  ign: string
  discord_name: string | null
  discord_avatar: string | null
}

export interface LevelTrendPoint {
  t: string
  avg: number
  members: number
}

export interface ActivityPoint {
  t: string
  online: number
}

export interface AttentionSettings {
  kick_risk_days: number
  inactive_days: number
  low_activity_days: number
  bottom_n: number
  stale_hours: number
  level_drop: number
}

export interface RankRequirement {
  key: string
  label: string
  level: number
  default_level: number
  editable: boolean
}

export type ActivityTiers = Record<'red' | 'yellow' | 'green' | 'blue' | 'white', number>

export interface ActivityConfig {
  d90: ActivityTiers
  total: ActivityTiers
}

export interface GuildConfigData {
  ranks: RankRequirement[]
  attention: AttentionSettings
  attention_defaults: AttentionSettings
  activity: ActivityConfig
  activity_defaults: ActivityConfig
  minecraft_version: string
  minecraft_version_default: string
  minecraft_versions: string[]
  updated_by: string | null
  updated_at: string | null
}

export interface WarpoutSettings {
  guild: string
  max_queue: number
  invite_timeout: number
}

export interface SharedSettings {
  warpout: WarpoutSettings
  warpout_defaults: WarpoutSettings
  censor_words: string[]
  guilds: { key: string; name: string }[]
  updated_by: string | null
  updated_at: string | null
}

export interface CatalogDye {
  dye_id: string
  dye_name: string
  weight: number
  hex: string
  role_id: string | null
  emoji_id: string | null
  unlocked_by: number
  odds: string
}

export interface DyeCatalog {
  dyes: CatalogDye[]
  total_weight: number
  unlocks_removed?: number
}

export interface LevelPerson {
  ign: string
  rank: string
  level: number
  uuid: string | null
  discord_name: string | null
  discord_avatar: string | null
  gain: number | null
  days_covered: number | null
}

export interface LevelLeaderboardData {
  days: number
  top: LevelPerson[]
  climbers: LevelPerson[]
}

export interface BotEmoji {
  id: string
  name: string
  animated: boolean
  source: 'application' | 'server'
}
