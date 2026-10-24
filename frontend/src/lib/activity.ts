import type { ActivityConfig, ActivityTiers } from '../types'

export const DEFAULT_ACTIVITY: ActivityConfig = {
  d90: { red: 10, yellow: 100, green: 250, blue: 500, white: 1000 },
  total: { red: 50, yellow: 500, green: 1250, blue: 2500, white: 5000 },
}

export const TIER_ORDER = ['red', 'yellow', 'green', 'blue', 'white'] as const

/** Tier 0 (dark red) is everything below `red`; tiers 1 to 5 start at each threshold. */
export function tierIndex(count: number, tiers: ActivityTiers): number {
  let tier = 0
  TIER_ORDER.forEach((k, i) => { if (count >= tiers[k]) tier = i + 1 })
  return tier
}

export const tierColor = (count: number, tiers: ActivityTiers): string => `var(--tier-${tierIndex(count, tiers)})`

export const TIER_NAMES = ['Dark red', 'Red', 'Yellow', 'Green', 'Blue', 'White']
