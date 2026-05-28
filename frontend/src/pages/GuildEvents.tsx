import { useParams } from 'react-router-dom'

const GUILD_NAMES: Record<string, string> = {
  bk: 'Bumble Kindergarten',
  bu: 'Bumble University',
}

export default function GuildEvents() {
  const { key } = useParams<{ key: string }>()
  const guildName = key ? GUILD_NAMES[key] ?? key.toUpperCase() : 'this guild'

  return (
    <div>
      <div className="header-row">
        <div className="page-title" style={{ marginBottom: 0 }}>Events</div>
      </div>

      <div className="card events-empty-state">
        <div className="events-empty-icon">📋</div>
        <div className="events-empty-title">No active events for {guildName}</div>
        <div className="events-empty-sub">
          Events can be run for a single guild or both guilds at once. Check back soon.
        </div>
      </div>
    </div>
  )
}
