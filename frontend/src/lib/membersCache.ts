import { api } from '../api'
import type { GuildMember } from '../types'

/** Loading the member list makes the bot run /guild list in-game, so it is cached
 * and shared between the Overview and Members pages instead of re-fetched per page. */
const TTL = 5 * 60 * 1000
const cache = new Map<string, { members: GuildMember[]; at: number }>()

export function getCachedMembers(key: string): GuildMember[] | undefined {
  return cache.get(key)?.members
}

export async function loadMembers(key: string, force = false): Promise<GuildMember[]> {
  const hit = cache.get(key)
  if (!force && hit && Date.now() - hit.at < TTL) return hit.members
  const res = await api.guildMembers(key)
  cache.set(key, { members: res.members, at: Date.now() })
  return res.members
}

export function setCachedMembers(key: string, members: GuildMember[]) {
  const hit = cache.get(key)
  cache.set(key, { members, at: hit?.at ?? Date.now() })
}

export function clearCachedMembers(key: string) {
  cache.delete(key)
}
