import type { ReactNode } from 'react'

/** Minecraft avatar + IGN (+ optional badge/uuid), used by every member/leaderboard table. */
export function PlayerIdentityCell({ uuid, ign, badge, avatarSize = 32 }: {
  uuid: string | null
  ign: string
  badge?: ReactNode
  avatarSize?: number
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: -4 }}>
      {uuid
        ? <img className="hex-avatar" src={`https://mc-heads.net/avatar/${uuid}/${avatarSize}`} alt="" style={{ width: avatarSize, height: avatarSize }} />
        : <div className="hex-avatar" style={{ width: avatarSize, height: avatarSize }} />
      }
      <div>
        <div style={{ fontWeight: 500 }}>
          {ign}
          {badge}
        </div>
        {uuid && <div className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>{uuid}</div>}
      </div>
    </div>
  )
}

/** Discord avatar + name (+ optional id/actions), or an em-dash placeholder when unlinked. */
export function DiscordIdentityCell({ name, avatar, id, actions, emptyActions }: {
  name: string | null
  avatar: string | null
  id?: string | null
  actions?: ReactNode
  emptyActions?: ReactNode
}) {
  if (!name) {
    return (
      <div>
        <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>—</span>
        {emptyActions}
      </div>
    )
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: -4 }}>
      {avatar
        ? <img src={avatar} alt="" style={{ width: 32, height: 32, borderRadius: '50%', flexShrink: 0 }} />
        : <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--surface3)', flexShrink: 0 }} />
      }
      <div>
        <div style={{ fontWeight: 500 }}>{name}</div>
        {id && <div className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>{id}</div>}
        {actions}
      </div>
    </div>
  )
}
