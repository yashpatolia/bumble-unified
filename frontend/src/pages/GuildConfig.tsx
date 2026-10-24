import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import { TIER_NAMES, TIER_ORDER } from '../lib/activity'
import { getAttention } from '../lib/attention'
import { loadGuildConfig, setCachedGuildConfig } from '../lib/guildConfig'
import { loadMembers } from '../lib/membersCache'
import type { ActivityConfig, AttentionSettings, GuildConfigData, GuildMember } from '../types'

type AttentionKey = keyof AttentionSettings
type Period = 'd90' | 'total'

const PERIODS: { id: Period; title: string; sub: string; field: 'messages_90d' | 'messages_total' }[] = [
  { id: 'd90', title: 'Messages, last 90 days', sub: 'Colour of the 90-day count on the Members page', field: 'messages_90d' },
  { id: 'total', title: 'Messages, all time', sub: 'Colour of the all-time count on the Members page', field: 'messages_total' },
]

const ATTENTION_FIELDS: { key: AttentionKey; label: string; help: string; unit: string }[] = [
  { key: 'low_activity_days', label: 'Low activity after', help: 'Days since last login before a member shows as low activity.', unit: 'days' },
  { key: 'inactive_days', label: 'Inactive after', help: 'Days since last login before a member shows as inactive.', unit: 'days' },
  { key: 'kick_risk_days', label: 'Kick risk after', help: 'Days since last login before a member shows as a kick risk.', unit: 'days' },
  { key: 'bottom_n', label: 'Only check the lowest', help: 'Inactivity warnings only apply to this many lowest-level members. Use 0 to check everyone.', unit: 'members' },
  { key: 'stale_hours', label: 'Stats are stale after', help: 'Hours since a member\'s stats were last refreshed.', unit: 'hours' },
  { key: 'level_drop', label: 'Flag a level drop of more than', help: 'Levels lost over 90 days. 0 flags any drop.', unit: 'levels' },
]

const toNum = (v: string): number | null => (v.trim() !== '' && /^\d+$/.test(v.trim()) ? Number(v.trim()) : null)

export default function GuildConfig() {
  const { key } = useParams<{ key: string }>()
  const { me } = useAuth()
  const canEdit = !!(me?.can_manage_config || me?.is_admin || me?.is_owner)

  const [data, setData] = useState<GuildConfigData | null>(null)
  const [rankForm, setRankForm] = useState<Record<string, string>>({})
  const [attnForm, setAttnForm] = useState<Record<string, string>>({})
  const [actForm, setActForm] = useState<Record<Period, Record<string, string>>>({ d90: {}, total: {} })
  const [members, setMembers] = useState<GuildMember[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const apply = (d: GuildConfigData) => {
    setData(d)
    setRankForm(Object.fromEntries(d.ranks.map(r => [r.key, String(r.level)])))
    setAttnForm(Object.fromEntries(Object.entries(d.attention).map(([k, v]) => [k, String(v)])))
    setActForm({
      d90: Object.fromEntries(TIER_ORDER.map(k => [k, String(d.activity.d90[k])])),
      total: Object.fromEntries(TIER_ORDER.map(k => [k, String(d.activity.total[k])])),
    })
  }

  useEffect(() => {
    if (!key) return
    setData(null)
    setLoadError(null)
    loadGuildConfig(key, true).then(apply).catch(e => setLoadError(e instanceof Error ? e.message : 'Failed to load config'))
    loadMembers(key).then(setMembers).catch(() => setMembers([]))
  }, [key])

  // Parsed draft values (null where the input is not a whole number yet).
  const rankDraft = useMemo(() => data?.ranks.map(r => ({ ...r, draft: r.editable ? toNum(rankForm[r.key] ?? '') : r.level })) ?? [], [data, rankForm])
  const attnDraft = useMemo(() => {
    const out: Partial<Record<AttentionKey, number | null>> = {}
    for (const f of ATTENTION_FIELDS) out[f.key] = toNum(attnForm[f.key] ?? '')
    return out
  }, [attnForm])

  const rankErrors = useMemo(() => {
    const errs: Record<string, string> = {}
    let prev: number | null = null
    for (const r of rankDraft) {
      if (r.draft == null) { errs[r.key] = 'Enter a whole number'; prev = null; continue }
      if (r.editable && r.draft > 10000) errs[r.key] = 'At most 10000'
      else if (r.editable && prev != null && r.draft <= prev) errs[r.key] = `Must be above ${prev}`
      prev = r.draft
    }
    return errs
  }, [rankDraft])

  const attnError = useMemo(() => {
    const d = attnDraft
    if (ATTENTION_FIELDS.some(f => d[f.key] == null)) return 'Every field needs a whole number.'
    if (!(d.low_activity_days! >= 1 && d.low_activity_days! < d.inactive_days! && d.inactive_days! < d.kick_risk_days!)) return 'Days must increase: low activity, then inactive, then kick risk.'
    if (d.kick_risk_days! > 3650) return 'Kick risk can be at most 3650 days.'
    if (d.stale_hours! < 1 || d.stale_hours! > 720) return 'Stale hours must be between 1 and 720.'
    if (d.bottom_n! > 1000) return 'Members checked can be at most 1000.'
    return null
  }, [attnDraft])

  // Per period: each tier must be a whole number above the one before it.
  const actErrors = useMemo(() => {
    const out: Record<Period, Record<string, string>> = { d90: {}, total: {} }
    for (const p of PERIODS) {
      let prev = 0
      for (const k of TIER_ORDER) {
        const n = toNum(actForm[p.id][k] ?? '')
        if (n == null) { out[p.id][k] = 'Enter a whole number'; prev = 0; continue }
        if (n <= prev) out[p.id][k] = prev === 0 ? 'Must be at least 1' : `Must be above ${prev}`
        prev = n
      }
    }
    return out
  }, [actForm])
  const actInvalid = PERIODS.some(p => Object.keys(actErrors[p.id]).length > 0)

  const valid = Object.keys(rankErrors).length === 0 && !attnError && !actInvalid
  const dirty = !!data && (
    data.ranks.some(r => r.editable && String(r.level) !== (rankForm[r.key] ?? '')) ||
    ATTENTION_FIELDS.some(f => String(data.attention[f.key]) !== (attnForm[f.key] ?? '')) ||
    PERIODS.some(p => TIER_ORDER.some(k => String(data.activity[p.id][k]) !== (actForm[p.id][k] ?? '')))
  )

  // What the draft would do to the current roster, so changes are not made blind.
  const preview = useMemo(() => {
    if (!members || !valid || !data) return null
    const draft = Object.fromEntries(ATTENTION_FIELDS.map(f => [f.key, attnDraft[f.key] as number])) as unknown as AttentionSettings
    const items = getAttention(members, draft).filter(i => ['kick-risk', 'inactive', 'low-activity', 'dropped', 'stale'].includes(i.id))
    const bands = rankDraft.map((r, i) => {
      const next = rankDraft[i + 1]
      const lo = r.draft as number
      const hi = next ? (next.draft as number) : Infinity
      return members.filter(m => m.skyblock_level != null && m.skyblock_level > lo && m.skyblock_level <= hi).length
    })
    return { items, bands }
  }, [members, valid, data, attnDraft, rankDraft])

  const save = async () => {
    if (!key || !data || !valid) return
    setSaving(true)
    setSaveError(null)
    setSaved(false)
    try {
      const ranks = Object.fromEntries(data.ranks.filter(r => r.editable).map(r => [r.key, Number(rankForm[r.key])]))
      const attention = Object.fromEntries(ATTENTION_FIELDS.map(f => [f.key, Number(attnForm[f.key])])) as unknown as AttentionSettings
      const activity = Object.fromEntries(PERIODS.map(p => [p.id, Object.fromEntries(TIER_ORDER.map(k => [k, Number(actForm[p.id][k])]))])) as unknown as ActivityConfig
      const next = await api.saveGuildConfig(key, { ranks, attention, activity })
      setCachedGuildConfig(key, next)
      apply(next)
      setSaved(true)
      setTimeout(() => setSaved(false), 4000)
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (loadError) return <p className="error-text">{loadError}</p>
  if (!data) return <p className="text-muted">Loading...</p>

  // Highest rank first reads like a ladder; the lowest rank is the default.
  const ladder = [...rankDraft].map((r, i) => ({ ...r, i })).reverse()

  return (
    <div>
      <div className="crumb reveal">{key?.toUpperCase()} / Config</div>
      <div className="page-head reveal" style={{ '--i': 1 } as React.CSSProperties}>
        <h1 className="page-title">Config</h1>
        {canEdit && (
          <div className="head-actions">
            {saved && <span className="badge badge-on">Saved</span>}
            <button className="btn btn-primary" onClick={save} disabled={!dirty || !valid || saving}>{saving ? 'Saving...' : 'Save changes'}</button>
          </div>
        )}
      </div>

      {!canEdit && (
        <p className="badge badge-off" style={{ marginBottom: 14, whiteSpace: 'normal' }}>
          You can view these settings. Changing them needs the Manage Config permission.
        </p>
      )}
      {saveError && <p className="error-text">{saveError}</p>}

      <div className="grid-eq">
        <div className="stack">
        <div className="card reveal" style={{ '--i': 2 } as React.CSSProperties}>
          <div className="card-head">
            <span className="card-title">Rank requirements</span>
            <span className="card-sub">Skyblock level needed for each guild rank</span>
          </div>
          <p className="card-sub" style={{ padding: '0 20px 10px' }}>
            The bot promotes and demotes members automatically to match their level. A member needs a level <b>above</b> the number to hold the rank. The lowest rank is the default and has no requirement.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th style={{ width: 260 }}>Rank</th><th>Level above</th></tr>
              </thead>
              <tbody>
                {ladder.map(r => (
                  <tr key={r.key}>
                    <td>
                      <div className="p-name">{r.label}</div>
                      <div className="p-sub mono">{r.key}</div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                      {r.editable ? (
                        <>
                          <input
                            className="form-input"
                            style={{ width: 110, ...(rankErrors[r.key] ? { borderColor: 'var(--danger)' } : {}) }}
                            inputMode="numeric"
                            value={rankForm[r.key] ?? ''}
                            disabled={!canEdit}
                            onChange={e => { setRankForm(f => ({ ...f, [r.key]: e.target.value })); setSaved(false) }}
                            aria-label={`${r.label} level requirement`}
                          />
                          {rankErrors[r.key] && <div className="error-text" style={{ margin: '4px 0 0', fontSize: 12 }}>{rankErrors[r.key]}</div>}
                        </>
                      ) : (
                        <span className="badge badge-off">Default rank</span>
                      )}
                      {preview && <span className="card-sub num">{preview.bands[r.i]} {preview.bands[r.i] === 1 ? 'member' : 'members'} in this range</span>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
          <div className="card reveal" style={{ '--i': 3 } as React.CSSProperties}>
            <div className="card-head">
              <span className="card-title">Preview</span>
              <span className="card-sub">Against the current roster</span>
            </div>
            <div className="card-pad" style={{ paddingTop: 4 }}>
              {!valid ? (
                <span className="card-sub">Fix the highlighted values to see the effect.</span>
              ) : !preview ? (
                <span className="card-sub">Loading roster...</span>
              ) : preview.items.length === 0 ? (
                <span className="card-sub">No one would be flagged with these values.</span>
              ) : (
                <div className="chips">
                  {preview.items.map(i => <span key={i.id} className={`badge badge-${i.tone === 'danger' ? 'danger' : i.tone === 'warn' ? 'warn' : ''}`}>{i.label.split(' (')[0]} {i.members.length}</span>)}
                </div>
              )}
            </div>
          </div>
        </div>

        <div>
          <div className="card reveal" style={{ '--i': 3 } as React.CSSProperties}>
            <div className="card-head">
              <span className="card-title">Needs attention</span>
              <span className="card-sub">When members get flagged</span>
            </div>
            <div className="attn-fields">
              {ATTENTION_FIELDS.map(f => (
                <div key={f.key} className="attn-field">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                    <label className="p-name" htmlFor={`attn-${f.key}`}>{f.label}</label>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <input
                        id={`attn-${f.key}`}
                        className="form-input"
                        style={{ width: 84, textAlign: 'right' }}
                        inputMode="numeric"
                        value={attnForm[f.key] ?? ''}
                        disabled={!canEdit}
                        onChange={e => { setAttnForm(a => ({ ...a, [f.key]: e.target.value })); setSaved(false) }}
                      />
                      <span className="card-sub" style={{ width: 52 }}>{f.unit}</span>
                    </span>
                  </div>
                  <div className="card-sub">{f.help} Default {data.attention_defaults[f.key]}.</div>
                </div>
              ))}
              {attnError && <p className="error-text" style={{ marginTop: 10 }}>{attnError}</p>}
            </div>
          </div>

        </div>
      </div>

      <div className="grid-eq" style={{ marginTop: 16 }}>
        {PERIODS.map((p, pi) => {
          const thresholds = TIER_ORDER.map(k => toNum(actForm[p.id][k] ?? ''))
          const rows = TIER_NAMES.map((name, t) => {
            const lo = t === 0 ? 0 : thresholds[t - 1]
            const hi = t === 5 ? null : thresholds[t]
            const count = members ? members.filter(m => {
              const v = (m[p.field] ?? 0) as number
              return lo != null && v >= lo && (hi == null || v < hi)
            }).length : null
            return { name, t, lo, hi, count }
          })
          return (
            <div key={p.id} className="card reveal" style={{ '--i': 5 + pi } as React.CSSProperties}>
              <div className="card-head">
                <span className="card-title">{p.title}</span>
                <span className="card-sub">{p.sub}</span>
              </div>
              <div style={{ padding: '2px 20px 12px' }}>
                {rows.map(r => {
                  const k = TIER_ORDER[r.t - 1]
                  const err = r.t > 0 ? actErrors[p.id][k] : undefined
                  return (
                    <div key={r.t} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '9px 0', borderTop: r.t === 0 ? 'none' : '1px solid var(--border)' }}>
                      <span style={{ width: 12, height: 12, borderRadius: 4, background: `var(--tier-${r.t})`, flexShrink: 0, boxShadow: 'inset 0 0 0 1px var(--border-strong)' }} />
                      <span className="p-name" style={{ width: 84 }}>{r.name}</span>
                      {r.t === 0 ? (
                        <span className="card-sub" style={{ width: 150 }}>below {thresholds[0] ?? '?'}</span>
                      ) : (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 8, width: 150, whiteSpace: 'nowrap' }}>
                          <input
                            className="form-input"
                            style={{ width: 86, textAlign: 'right', ...(err ? { borderColor: 'var(--danger)' } : {}) }}
                            inputMode="numeric"
                            value={actForm[p.id][k] ?? ''}
                            disabled={!canEdit}
                            aria-label={`${p.title}, ${r.name} starts at`}
                            onChange={e => { setActForm(a => ({ ...a, [p.id]: { ...a[p.id], [k]: e.target.value } })); setSaved(false) }}
                          />
                          <span className="card-sub">and up</span>
                        </span>
                      )}
                      <span className="card-sub num" style={{ marginLeft: 'auto' }}>{r.count == null ? '' : `${r.count} ${r.count === 1 ? 'member' : 'members'}`}</span>
                      {err && <span className="error-text" style={{ margin: 0, fontSize: 12 }}>{err}</span>}
                    </div>
                  )
                })}
                {pi === 1 && <p className="card-sub" style={{ marginTop: 6 }}>The White tier shows as white in dark mode and near-black in light mode. All-time counts begin when message tracking started.</p>}
              </div>
            </div>
          )
        })}
      </div>

      {data.updated_by && data.updated_at && (
        <p className="card-sub" style={{ marginTop: 14 }}>
          Last changed by {data.updated_by} on {new Date(data.updated_at).toLocaleString()}.
        </p>
      )}
    </div>
  )
}
