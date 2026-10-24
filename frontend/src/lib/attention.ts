import type { AttentionSettings, GuildMember } from '../types'
import { DEFAULT_ATTENTION } from './guildConfig'

const DAY_MS = 86400000

export type AttentionTone = 'danger' | 'warn' | 'info'

export interface AttentionItem {
  id: string
  label: string
  /** Compact label for table badges. */
  short: string
  tone: AttentionTone
  members: GuildMember[]
}

/** The three inactivity warnings share one rule: only the `bottom_n` lowest-level members
 * can be flagged (0 means everyone), and the tier comes from days since last login. */
function warnTiers(members: GuildMember[], s: AttentionSettings) {
  const withLevel = members
    .filter(m => m.skyblock_level != null)
    .sort((a, b) => (a.skyblock_level ?? 0) - (b.skyblock_level ?? 0))
  const eligible = s.bottom_n > 0 ? new Set(withLevel.slice(0, s.bottom_n).map(m => m.ign)) : null
  const tiers = { kick: [] as GuildMember[], inactive: [] as GuildMember[], low: [] as GuildMember[] }
  for (const m of members) {
    if (m.last_login == null || m.excused) continue
    if (eligible && !eligible.has(m.ign)) continue
    const days = (Date.now() - m.last_login) / DAY_MS
    if (days > s.kick_risk_days) tiers.kick.push(m)
    else if (days > s.inactive_days) tiers.inactive.push(m)
    else if (days > s.low_activity_days) tiers.low.push(m)
  }
  return tiers
}

/** Everything an admin should look at, most severe first. Empty groups are dropped. */
export function getAttention(members: GuildMember[], s: AttentionSettings = DEFAULT_ATTENTION): AttentionItem[] {
  const tiers = warnTiers(members, s)
  const nowSecs = Date.now() / 1000
  const all: AttentionItem[] = [
    { id: 'kick-risk', label: `Kick risk (${s.kick_risk_days}+ days offline)`, short: 'Kick risk', tone: 'danger', members: tiers.kick },
    { id: 'inactive', label: `Inactive (${s.inactive_days}+ days)`, short: 'Inactive', tone: 'warn', members: tiers.inactive },
    { id: 'low-activity', label: `Low activity (${s.low_activity_days}+ days)`, short: 'Low activity', tone: 'warn', members: tiers.low },
    { id: 'dropped', label: 'Level dropped in 90 days', short: 'Level drop', tone: 'warn', members: members.filter(m => m.level_gain_90d != null && m.level_gain_90d < -s.level_drop) },
    { id: 'excused', label: 'Excused', short: 'Excused', tone: 'info', members: members.filter(m => m.excused) },
    { id: 'unlinked', label: 'Discord not linked', short: 'Unlinked', tone: 'info', members: members.filter(m => !m.discord_name) },
    { id: 'stale', label: `Stats older than ${s.stale_hours} ${s.stale_hours === 1 ? 'hour' : 'hours'}`, short: 'Stale stats', tone: 'info', members: members.filter(m => m.stats_fetched_at == null || nowSecs - m.stats_fetched_at > s.stale_hours * 3600) },
  ]
  return all.filter(i => i.members.length > 0)
}

export function previewNames(members: GuildMember[], max = 3): string {
  const names = members.slice(0, max).map(m => m.ign).join(', ')
  return members.length > max ? `${names} +${members.length - max}` : names
}
