/** Small inline-SVG line-icon set for the sidebar and page chrome.
 * Stroke-based, 18x18, inherits color via currentColor, no icon library dependency. */
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

/** Rounded bot/guild glyph, used for the guild nav groups. */
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

export function SunIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4" />
    </svg>
  )
}

export function MoonIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
    </svg>
  )
}

export function MenuIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  )
}

export function CheckCircleIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="m8 12.5 2.8 2.8L16 9.5" />
    </svg>
  )
}

export function SearchIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4" />
    </svg>
  )
}

export function ArrowRightIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  )
}

export function SlidersIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M4 7h9M17 7h3M4 17h3M11 17h9" />
      <circle cx="15" cy="7" r="2" />
      <circle cx="9" cy="17" r="2" />
    </svg>
  )
}

export function LinkIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" />
      <path d="M14 10a4 4 0 0 0-5.7 0l-3 3A4 4 0 0 0 11 18.7l1-1" />
    </svg>
  )
}

export function UnlinkIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" />
      <path d="M14 10a4 4 0 0 0-5.7 0l-3 3A4 4 0 0 0 11 18.7l1-1" />
      <path d="M4 4l16 16" />
    </svg>
  )
}

export function PencilIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z" />
      <path d="m13.5 6.5 4 4" />
    </svg>
  )
}

export function CalendarIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <rect x="4" y="5.5" width="16" height="14.5" rx="2.5" />
      <path d="M4 10h16M8.5 3.5v4M15.5 3.5v4" />
    </svg>
  )
}

export function UserMinusIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <circle cx="9.5" cy="8" r="3.5" />
      <path d="M3 20c.5-3.4 3-5.3 6.5-5.3 1.4 0 2.6.3 3.6.9" />
      <path d="M16 15.5h5" />
    </svg>
  )
}

export function TrashIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M4 7h16" />
      <path d="M10 11v6M14 11v6" />
      <path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12" />
      <path d="M9 7V4h6v3" />
    </svg>
  )
}

export function PlusIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

export function GlobeIcon(p: IconProps) {
  return (
    <svg {...base} {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z" />
    </svg>
  )
}
