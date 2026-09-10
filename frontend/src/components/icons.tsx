/** Small inline-SVG line-icon set for the sidebar and page chrome.
 * Stroke-based, 18x18, inherits color via currentColor — no icon library dependency. */
import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

const base = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

export function HomeIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5.5 10v9.5a1 1 0 0 0 1 1H9a1 1 0 0 0 1-1V15a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v4.5a1 1 0 0 0 1 1h2.5a1 1 0 0 0 1-1V10" />
    </svg>
  )
}

/** Rounded bot/guild glyph — used for the guild nav groups. */
export function BotIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <rect x="4" y="8.5" width="16" height="11" rx="3.5" />
      <path d="M12 8.5V5.5" />
      <circle cx="12" cy="4" r="1.3" />
      <circle cx="9" cy="14" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="15" cy="14" r="1.3" fill="currentColor" stroke="none" />
      <path d="M9.5 17.5h5" />
    </svg>
  )
}

export function UsersIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3.5 19c0-3 2.5-5 5.5-5s5.5 2 5.5 5" />
      <path d="M16 6.5c1.5.3 2.6 1.6 2.6 3.1s-1.1 2.8-2.6 3.1" />
      <path d="M15.5 14c2.4.4 4 2.2 4 4.6" />
    </svg>
  )
}

export function TrophyIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M7 4h10v5a5 5 0 0 1-10 0z" />
      <path d="M7 5.5H4v1.5A3 3 0 0 0 7 10" />
      <path d="M17 5.5h3v1.5A3 3 0 0 1 17 10" />
      <path d="M12 14v3" />
      <path d="M8.5 20.5h7" />
      <path d="M10 17.5h4l.7 3H9.3z" />
    </svg>
  )
}

export function DropletIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z" />
    </svg>
  )
}

export function ShieldIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M12 3.5 19 6v6c0 5-3.5 7.5-7 8.5-3.5-1-7-3.5-7-8.5V6z" />
      <path d="M9 12l2 2 4-4.5" />
    </svg>
  )
}

export function GearIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <circle cx="12" cy="12" r="3.2" />
      <path d="M12 4.5v2M12 17.5v2M4.5 12h2M17.5 12h2M6.8 6.8l1.4 1.4M15.8 15.8l1.4 1.4M6.8 17.2l1.4-1.4M15.8 8.2l1.4-1.4" />
    </svg>
  )
}

export function LogoutIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3" />
      <path d="M15 8l4 4-4 4" />
      <path d="M19 12H9" />
    </svg>
  )
}

export function ChevronRightIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M9 5l7 7-7 7" />
    </svg>
  )
}
