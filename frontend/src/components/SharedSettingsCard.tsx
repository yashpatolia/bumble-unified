import { useEffect, useState } from 'react'
import { api } from '../api'
import type { SharedSettings } from '../types'

const toNum = (v: string): number | null => (v.trim() !== '' && /^\d+$/.test(v.trim()) ? Number(v.trim()) : null)
const parseWords = (v: string) => Array.from(new Set(v.split(/[\s,]+/).map(w => w.trim().toLowerCase()).filter(Boolean)))

/** Warpout and censored-word settings shared by both guilds (Config page, below the
 * per-guild cards). Saves on its own, separately from the guild's settings. */
export function SharedSettingsCard({ canEdit }: { canEdit: boolean }) {
  const [data, setData] = useState<SharedSettings | null>(null)
  const [guild, setGuild] = useState('')
  const [maxQueue, setMaxQueue] = useState('')
  const [inviteTimeout, setInviteTimeout] = useState('')
  const [words, setWords] = useState('')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const apply = (d: SharedSettings) => {
    setData(d)
    setGuild(d.warpout.guild)
    setMaxQueue(String(d.warpout.max_queue))
    setInviteTimeout(String(d.warpout.invite_timeout))
    setWords(d.censor_words.join(', '))
  }

  useEffect(() => {
    api.sharedSettings().then(apply).catch(e => setLoadError(e instanceof Error ? e.message : 'Failed to load settings'))
  }, [])

  if (loadError) return <p className="error-text">{loadError}</p>
  if (!data) return <p className="text-muted">Loading...</p>

  const q = toNum(maxQueue)
  const t = toNum(inviteTimeout)
  const error =
    q == null || q < 1 || q > 50 ? 'Queue size must be a whole number from 1 to 50.' :
    t == null || t < 10 || t > 60 ? 'Invite timeout must be a whole number from 10 to 60 seconds.' :
    parseWords(words).some(w => !/^[a-z0-9]{2,30}$/.test(w)) ? 'Censored words are 2-30 letters or digits each, separated by commas or spaces.' :
    null
  const dirty =
    guild !== data.warpout.guild || maxQueue !== String(data.warpout.max_queue) ||
    inviteTimeout !== String(data.warpout.invite_timeout) || parseWords(words).join(',') !== data.censor_words.join(',')

  const save = async () => {
    if (error) return
    setSaving(true)
    setSaveError(null)
    setSaved(false)
    try {
      apply(await api.saveSharedSettings({
        warpout: { guild, max_queue: q as number, invite_timeout: t as number },
        censor_words: parseWords(words),
      }))
      setSaved(true)
      setTimeout(() => setSaved(false), 4000)
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const d = data.warpout_defaults
  return (
    <div className="card reveal" style={{ '--i': 8 } as React.CSSProperties}>
      <div className="card-head">
        <span className="card-title">Warpout and chat</span>
        {canEdit && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {saved && <span className="badge badge-on">Saved</span>}
            <button className="btn btn-primary btn-sm" onClick={save} disabled={!dirty || !!error || saving}>{saving ? 'Saving...' : 'Save'}</button>
          </span>
        )}
      </div>
      <div className="attn-fields">
        <div className="attn-field">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <label className="p-name" htmlFor="wo-guild">Warpout bot</label>
            <select id="wo-guild" className="form-input" style={{ width: 210 }} value={guild} disabled={!canEdit}
              onChange={e => { setGuild(e.target.value); setSaved(false) }}>
              {data.guilds.map(g => <option key={g.key} value={g.key}>{g.name}</option>)}
            </select>
          </div>
          <div className="card-sub">Whose bridge bot does every .warpout, from either guild or Discord. It needs Minecraft 26.1. Default {d.guild.toUpperCase()}.</div>
        </div>
        <div className="attn-field">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <label className="p-name" htmlFor="wo-queue">Queue size</label>
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input id="wo-queue" className="form-input" style={{ width: 84, textAlign: 'right' }} inputMode="numeric"
                value={maxQueue} disabled={!canEdit} onChange={e => { setMaxQueue(e.target.value); setSaved(false) }} />
              <span className="card-sub" style={{ width: 60 }}>requests</span>
            </span>
          </div>
          <div className="card-sub">How many warpouts can wait in line, including the one running. Default {d.max_queue}.</div>
        </div>
        <div className="attn-field">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <label className="p-name" htmlFor="wo-timeout">Invite timeout</label>
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input id="wo-timeout" className="form-input" style={{ width: 84, textAlign: 'right' }} inputMode="numeric"
                value={inviteTimeout} disabled={!canEdit} onChange={e => { setInviteTimeout(e.target.value); setSaved(false) }} />
              <span className="card-sub" style={{ width: 60 }}>seconds</span>
            </span>
          </div>
          <div className="card-sub">How long to wait for the player to accept the party invite. Hypixel expires invites at 60. Default {d.invite_timeout}.</div>
        </div>
        <div className="attn-field" style={{ gridColumn: '1 / -1' }}>
          <label className="p-name" htmlFor="censor-words">Extra censored words</label>
          <textarea id="censor-words" className="form-input" rows={2} style={{ width: '100%', marginTop: 8, resize: 'vertical' }}
            value={words} disabled={!canEdit} placeholder="word1, word2"
            onChange={e => { setWords(e.target.value); setSaved(false) }} />
          <div className="card-sub">Masked in the panel's guild chat on top of the built-in list (Discord and in-game chat are not censored). Comma or space separated.</div>
        </div>
      </div>
      {(error || saveError) && <p className="error-text" style={{ padding: '0 20px 14px' }}>{saveError ?? error}</p>}
      {data.updated_by && data.updated_at && (
        <p className="card-sub" style={{ padding: '0 20px 14px' }}>Last changed by {data.updated_by} on {new Date(data.updated_at).toLocaleString()}.</p>
      )}
    </div>
  )
}
