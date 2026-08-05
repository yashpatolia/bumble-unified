export interface RelativeTimeOptions {
  /** Show "just now" when the elapsed time is under this many minutes. */
  justNowUnderMins?: number
  /** 'years' extends past days into month/year tiers; default stops at days. */
  maxTier?: 'days' | 'years'
}

/** Format a millisecond duration (already `Date.now() - timestamp`) as "Xm ago" / "Xh ago" / etc. */
export function formatRelativeTime(diffMs: number, opts: RelativeTimeOptions = {}): string {
  const mins = Math.floor(diffMs / 60000)
  if (opts.justNowUnderMins != null && mins < opts.justNowUnderMins) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(diffMs / 3600000)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(diffMs / 86400000)
  if (opts.maxTier !== 'years') return `${days}d ago`
  if (days < 30) return `${days}d ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months}mo ago`
  return `${Math.floor(months / 12)}y ago`
}
