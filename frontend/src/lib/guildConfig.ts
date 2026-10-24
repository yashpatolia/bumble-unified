import { api } from '../api'
import type { AttentionSettings, GuildConfigData } from '../types'

/** Built-in fallback so lists still render if the config request fails. Must match
 * ATTENTION_DEFAULTS in bot/lib/guild_settings.py. */
export const DEFAULT_ATTENTION: AttentionSettings = {
  kick_risk_days: 60,
  inactive_days: 30,
  low_activity_days: 14,
  bottom_n: 20,
  stale_hours: 2,
  level_drop: 0,
}

const TTL = 60 * 1000
const cache = new Map<string, { data: GuildConfigData; at: number }>()

export async function loadGuildConfig(key: string, force = false): Promise<GuildConfigData> {
  const hit = cache.get(key)
  if (!force && hit && Date.now() - hit.at < TTL) return hit.data
  const data = await api.guildConfig(key)
  cache.set(key, { data, at: Date.now() })
  return data
}

export function setCachedGuildConfig(key: string, data: GuildConfigData) {
  cache.set(key, { data, at: Date.now() })
}
