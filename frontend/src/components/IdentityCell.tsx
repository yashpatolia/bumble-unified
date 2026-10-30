import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

/** Minecraft avatar + IGN (+ optional badge), used by every member/leaderboard table. */
export function PlayerIdentityCell({ uuid, ign, badge, sub, to }: {
  uuid: string | null
  ign: string
  /** Makes the name a link (to the member's page). */
  to?: string
  badge?: ReactNode
  sub?: ReactNode
}) {
  return (
    <div className="player">
      {uuid ? <img src={`https://mc-heads.net/avatar/${uuid}/32`} alt="" /> : <div className="ph" />}
      <div style={{ minWidth: 0 }}>
        <div className="p-name">{to ? <Link to={to} className="p-link">{ign}</Link> : ign}{badge}</div>
        {sub && <div className="p-sub">{sub}</div>}
      </div>
    </div>
  )
}

/** Discord avatar + name (+ optional actions), or a muted "Not linked" when unlinked. */
export function DiscordIdentityCell({ name, avatar, actions, emptyActions }: {
  name: string | null
  avatar: string | null
  actions?: ReactNode
  emptyActions?: ReactNode
}) {
  if (!name) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span className="badge badge-warn">Not linked</span>
        {emptyActions}
      </div>
    )
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      {avatar
        ? <img className="avatar dc-avatar" src={avatar} alt="" width={26} height={26} />
        : <div className="avatar-fallback dc-avatar" style={{ width: 26, height: 26, fontSize: 11 }}>{name[0]?.toUpperCase()}</div>}
      <span style={{ fontWeight: 600 }}>{name}</span>
      {actions}
    </div>
  )
}
