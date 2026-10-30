import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { HistoryChart } from '../components/HistoryChart'
import { DiscordIdentityCell } from '../components/IdentityCell'
import { formatRelativeTime } from '../lib/time'
import type { MemberDetail, MemberEvent } from '../types'

const BOSSES: { key: string; name: string }[] = [
  { key: 'zombie', name: 'Revenant' }, { key: 'spider', name: 'Tarantula' }, { key: 'wolf', name: 'Sven' },
  { key: 'enderman', name: 'Voidgloom' }, { key: 'blaze', name: 'Inferno' }, { key: 'vampire', name: 'Riftstalker' },
]

const EVENT_TEXT: Record<string, (e: MemberEvent) => string> = {
  joined: e => `Joined ${e.guild}`,
  left: e => `Left ${e.guild}`,
  kicked: e => `Kicked from ${e.guild}`,
  promoted: e => `Promoted in ${e.guild}: ${e.detail.from} to ${e.detail.to}`,
  demoted: e => `Demoted in ${e.guild}: ${e.detail.from} to ${e.detail.to}`,
  renamed: e => `Changed name from ${e.detail.from} to ${e.detail.to}`,
}

const num = (n: number | null | undefined, digits = 0) => (n == null ? 'n/a' : n.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits }))
const gain = (n: number | null, digits = 0) => (n == null ? null : `${n >= 0 ? '+' : ''}${num(n, digits)}`)
const ago = (unixSeconds: number | null, unit: 's' | 'ms') =>
  unixSeconds ? formatRelativeTime(Date.now() - (unit === 's' ? unixSeconds * 1000 : unixSeconds), { justNowUnderMins: 2, maxTier: 'years' }) : 'never'

/** One member: current stats, rank progress, chat activity, dyes and 90 days of level, Catacombs
 * and slayer history. Reached by clicking a name on the Members or Leaderboard pages. */
export default function GuildMember() {
  const { key, ign } = useParams<{ key: string; ign: string }>()
  const [data, setData] = useState<MemberDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!key || !ign) return
    setData(null)
    setError(null)
    api.memberDetail(key, ign).then(setData).catch(e => setError(e instanceof Error ? e.message : 'Failed to load member'))
  }, [key, ign])

  const h = data?.history ?? []
  const first = <T,>(pick: (p: MemberDetail['history'][number]) => T | null) => h.map(pick).find(v => v != null) ?? null
  const last = <T,>(pick: (p: MemberDetail['history'][number]) => T | null) => [...h].reverse().map(pick).find(v => v != null) ?? null

  const stats = useMemo(() => {
    const cata = last(p => p.catacombs_level), cata0 = first(p => p.catacombs_level)
    const slayer = last(p => p.slayer_total), slayer0 = first(p => p.slayer_total)
    const lvl = last(p => p.level), lvl0 = first(p => p.level)
    const latestSlayer = last(p => p.slayer), firstSlayer = first(p => p.slayer)
    return {
      cata, cataGain: cata != null && cata0 != null ? cata - cata0 : null,
      slayer, slayerGain: slayer != null && slayer0 != null ? slayer - slayer0 : null,
      lvlGain: lvl != null && lvl0 != null ? lvl - lvl0 : null,
      latestSlayer, firstSlayer,
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  if (error) return <div><Link to={`/guilds/${key}/members`} className="crumb">Back to members</Link><p className="error-text">{error}</p></div>
  if (!data) return <p className="text-muted">Loading...</p>

  const span = h.length > 1 ? `since ${h[0].t}` : 'no history yet'
  const kpis = [
    { label: 'Skyblock level', value: num(data.level, 1), sub: stats.lvlGain != null ? `${gain(stats.lvlGain, 1)} ${span}` : span },
    { label: 'Catacombs', value: stats.cata != null ? num(stats.cata, 2) : 'n/a', sub: stats.cataGain != null ? `${gain(stats.cataGain, 2)} ${span}` : 'Tracked daily' },
    { label: 'Slayer XP', value: stats.slayer != null ? num(stats.slayer) : 'n/a', sub: stats.slayerGain != null ? `${gain(stats.slayerGain)} ${span}` : 'Tracked daily' },
    { label: 'Messages', value: data.messages_90d != null ? `${num(data.messages_90d)}` : 'n/a', sub: data.messages_total != null ? `${num(data.messages_total)} all time, 90 days shown` : 'No UUID yet' },
    { label: 'Last login', value: ago(data.last_login, 'ms'), sub: `Stats updated ${ago(data.stats_fetched_at, 's')}` },
  ]

  return (
    <div>
      <div className="crumb reveal"><Link to={`/guilds/${key}/members`}>{key?.toUpperCase()} / Members</Link> / {data.ign}</div>
      <div className="page-head reveal" style={{ '--i': 1 } as React.CSSProperties}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {data.uuid && <img src={`https://mc-heads.net/avatar/${data.uuid}/64`} alt="" width={48} height={48} style={{ borderRadius: 10 }} />}
          <div>
            <h1 className="page-title" style={{ margin: 0 }}>{data.ign}</h1>
            <div style={{ display: 'flex', gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
              <span className="badge">{data.rank || 'No rank'}</span>
              {data.joined_at
                ? <span className="card-sub" title={new Date(data.joined_at).toLocaleString()}>Joined {formatRelativeTime(Date.now() - new Date(data.joined_at).getTime(), { justNowUnderMins: 2, maxTier: 'years' })}</span>
                : data.tracked_since && <span className="card-sub">In the guild since at least {data.tracked_since}</span>}
              {data.excused && (
                <span className="badge" title={[data.excused.reason, data.excused.until ? `until ${data.excused.until}` : 'until removed'].filter(Boolean).join(', ')}>
                  Excused{data.excused.until ? ` until ${data.excused.until}` : ''}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="kpis">
        {kpis.map((k, i) => (
          <div key={k.label} className="card kpi reveal" style={{ '--i': 2 + i } as React.CSSProperties}>
            <div className="k-label">{k.label}</div>
            <div className="k-value num">{k.value}</div>
            <div className="k-sub">{k.sub}</div>
          </div>
        ))}
      </div>

      <div className="stack" style={{ marginBottom: 16 }}>
        <div className="card reveal" style={{ '--i': 7 } as React.CSSProperties}>
          <div className="card-head"><span className="card-title">Skyblock level</span><span className="card-sub">Daily, last 90 days</span></div>
          <HistoryChart height={340} points={h.map(p => ({ t: p.t, v: p.level }))} unit="level" decimals={1} ariaLabel={`${data.ign} Skyblock level over time`} />
        </div>
        <div className="card reveal" style={{ '--i': 8 } as React.CSSProperties}>
          <div className="card-head"><span className="card-title">Catacombs level</span><span className="card-sub">Daily, last 90 days</span></div>
          <HistoryChart height={340} points={h.map(p => ({ t: p.t, v: p.catacombs_level }))} unit="cata level" decimals={2} ariaLabel={`${data.ign} Catacombs level over time`} />
        </div>
        <div className="card reveal" style={{ '--i': 9 } as React.CSSProperties}>
          <div className="card-head"><span className="card-title">Slayer XP</span><span className="card-sub">All six bosses combined</span></div>
          <HistoryChart height={340} points={h.map(p => ({ t: p.t, v: p.slayer_total }))} unit="slayer xp" ariaLabel={`${data.ign} total slayer XP over time`} />
        </div>
      </div>

      <div className="grid-eq">
          <div className="card reveal" style={{ '--i': 7 } as React.CSSProperties}>
            <div className="card-head"><span className="card-title">Guild</span></div>
            <div className="card-pad" style={{ paddingTop: 4, display: 'grid', gap: 12 }}>
              <div>
                <div className="k-label">Rank</div>
                <div><b>{data.rank || 'None'}</b>
                  {data.next_rank
                    ? <span className="card-sub"> . next: {data.next_rank.label} above level {data.next_rank.level} ({Math.max(data.next_rank.level - (data.level ?? 0), 0).toFixed(1)} to go)</span>
                    : <span className="card-sub"> . top rank</span>}
                </div>
              </div>
              <div>
                <div className="k-label">Discord</div>
                <DiscordIdentityCell name={data.discord?.name ?? null} avatar={data.discord?.avatar ?? null} />
              </div>
              <div>
                <div className="k-label">Dyes</div>
                <div>{data.dyes_owned != null ? <><b>{data.dyes_owned}</b> <span className="card-sub">of {data.dyes_total} unlocked</span></> : <span className="card-sub">Needs a UUID</span>}</div>
              </div>
            </div>
          </div>

          <div className="card reveal" style={{ '--i': 8 } as React.CSSProperties}>
            <div className="card-head"><span className="card-title">Roster history</span><span className="card-sub">Joins, ranks, names</span></div>
            {data.events.length === 0 ? (
              <div className="chart-empty">Nothing recorded yet. Joins, leaves, promotions, demotions and name changes show up here from now on.</div>
            ) : (
              <ul style={{ listStyle: 'none', margin: 0, padding: '0 20px 14px', display: 'grid', gap: 10 }}>
                {data.events.map((e, i) => (
                  <li key={`${e.t}-${i}`} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                    <span>{EVENT_TEXT[e.kind]?.(e) ?? e.kind}</span>
                    <span className="card-sub" style={{ whiteSpace: 'nowrap' }} title={new Date(e.t).toLocaleString()}>
                      {formatRelativeTime(Date.now() - new Date(e.t).getTime(), { justNowUnderMins: 2, maxTier: 'years' })}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="card reveal" style={{ '--i': 9 } as React.CSSProperties}>
            <div className="card-head"><span className="card-title">Slayer bosses</span><span className="card-sub">XP now, and gained {span}</span></div>
            {!stats.latestSlayer ? <div className="chart-empty">Slayer XP is recorded once a day, so it shows up after the next refresh.</div> : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Boss</th><th>XP</th><th>Gained</th></tr></thead>
                  <tbody>
                    {BOSSES.map(b => {
                      const now = stats.latestSlayer?.[b.key] ?? 0
                      const before = stats.firstSlayer?.[b.key]
                      return (
                        <tr key={b.key}>
                          <td className="p-name">{b.name}</td>
                          <td className="num">{num(now)}</td>
                          <td className="num">{before == null || h.length < 2 ? '' : gain(now - before)}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
      </div>
    </div>
  )
}
