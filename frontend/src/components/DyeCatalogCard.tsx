import { useEffect, useState } from 'react'
import { api } from '../api'
import { Modal } from './Modal'
import { PencilIcon, PlusIcon, TrashIcon } from './icons'
import { isValidDiscordId } from '../lib/validators'
import type { BotEmoji, CatalogDye, DyeCatalog } from '../types'

type Form = { dye_id: string; dye_name: string; weight: string; hex: string; role_id: string; emoji_id: string }
const EMPTY: Form = { dye_id: '', dye_name: '', weight: '', hex: '', role_id: '', emoji_id: '' }

const formError = (f: Form, isNew: boolean, others: number): string | null => {
  if (isNew && !/^[a-z0-9_]{2,40}$/.test(f.dye_id)) return 'ID must be 2-40 lowercase letters, digits or underscores, e.g. mango_dye.'
  if (!f.dye_name.trim() || f.dye_name.trim().length > 40) return 'Name must be 1-40 characters.'
  const w = Number(f.weight)
  if (!f.weight.trim() || !Number.isFinite(w) || w <= 0 || w > 100) return 'Weight must be above 0 and at most 100.'
  if (others + w > 100) return `All weights together can't go above 100 (the others add up to ${+others.toFixed(6)}).`
  if (!/^#?[0-9a-fA-F]{6}$/.test(f.hex.trim())) return 'Colour must be a 6-digit hex code, e.g. FDBE02.'
  if (f.role_id.trim() && !isValidDiscordId(f.role_id.trim())) return 'Role must be a Discord role ID (17-20 digits).'
  if (f.emoji_id.trim() && !isValidDiscordId(f.emoji_id.trim())) return 'Emoji must be a Discord emoji ID (17-20 digits).'
  return null
}

// The bot's Discord emoji, straight from Discord's CDN by id (hidden if the id doesn't resolve).
function DyeEmoji({ id, size = 22 }: { id: string | null; size?: number }) {
  const [broken, setBroken] = useState(false)
  useEffect(() => setBroken(false), [id])
  if (!id || broken) return null
  return <img src={`https://cdn.discordapp.com/emojis/${id}.webp?size=${size * 2}`} alt="" width={size} height={size}
    style={{ objectFit: 'contain', flexShrink: 0 }} onError={() => setBroken(true)} />
}

const MAX_EMOJI_BYTES = 256 * 1024

const readBase64 = (file: File) => new Promise<string>((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(String(reader.result).split(',')[1] ?? '')
  reader.onerror = () => reject(new Error('Could not read that file'))
  reader.readAsDataURL(file)
})

/** Pick one of the bot's Discord emojis, or upload a new one (saved on the bot as an
 * application emoji, named after the dye id). Falls back to a plain ID box if the bot is offline. */
function EmojiPicker({ value, onChange, uploadName, canEdit }: {
  value: string; onChange: (id: string) => void; uploadName: string; canEdit: boolean
}) {
  const [emojis, setEmojis] = useState<BotEmoji[] | null>(null)
  const [offline, setOffline] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.dyeEmojis().then(d => { setEmojis(d.emojis); setOffline(!!d.offline) }).catch(() => { setEmojis([]); setOffline(true) })
  }, [])

  const name = uploadName.replace(/[^A-Za-z0-9_]/g, '').slice(0, 32)
  const upload = async (file: File | undefined) => {
    if (!file) return
    setError(null)
    if (file.size > MAX_EMOJI_BYTES) { setError('Emoji images can be at most 256 KB.'); return }
    setUploading(true)
    try {
      const made = await api.uploadDyeEmoji(name, await readBase64(file))
      setEmojis(list => [...(list ?? []), made].sort((a, b) => a.name.localeCompare(b.name)))
      onChange(made.id)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  if (emojis === null) return <span className="card-sub">Loading emojis...</span>
  if (offline && emojis.length === 0) {
    return (
      <div>
        <input className="form-input mono" style={{ width: '100%' }} inputMode="numeric" placeholder="Emoji ID" value={value}
          onChange={e => onChange(e.target.value.trim())} />
        <div className="card-sub" style={{ marginTop: 4 }}>The bot is offline, so its emojis can't be listed. Paste an emoji ID instead.</div>
      </div>
    )
  }
  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, maxHeight: 132, overflowY: 'auto', padding: 2 }}>
        <button type="button" className={`chip${value === '' ? ' active' : ''}`} onClick={() => onChange('')}>None</button>
        {emojis.map(e => (
          <button key={e.id} type="button" title={`${e.name} (${e.source})`} aria-label={e.name} aria-pressed={value === e.id}
            className={`icon-btn${value === e.id ? ' active' : ''}`} style={value === e.id ? { boxShadow: '0 0 0 2px var(--accent)' } : undefined}
            onClick={() => onChange(e.id)}>
            <DyeEmoji id={e.id} size={22} />
          </button>
        ))}
      </div>
      {canEdit && (
        <div style={{ marginTop: 8 }}>
          <label className={`btn btn-sm${uploading || !name ? ' disabled' : ''}`} style={{ cursor: uploading || !name ? 'not-allowed' : 'pointer', opacity: uploading || !name ? 0.6 : 1 }}>
            {uploading ? 'Uploading...' : 'Upload new emoji'}
            <input type="file" accept="image/png,image/jpeg,image/gif" hidden disabled={uploading || !name}
              onChange={e => { upload(e.target.files?.[0]); e.target.value = '' }} />
          </label>
          <span className="card-sub" style={{ marginLeft: 10 }}>{name ? `Saved as "${name}". PNG, JPG or GIF, up to 256 KB.` : 'Fill in the dye ID first.'}</span>
        </div>
      )}
      {error && <p className="error-text" style={{ margin: '6px 0 0' }}>{error}</p>}
    </div>
  )
}

const oddsFor = (weight: number) => (weight > 0 ? `1 in ${Math.round(100 / weight).toLocaleString()}` : '')

/** Dye catalog editor (Config page, shared by both guilds): drop weight, colour, Discord
 * colour role and emoji per dye, plus adding and removing dyes. */
export function DyeCatalogCard({ canEdit }: { canEdit: boolean }) {
  const [data, setData] = useState<DyeCatalog | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [editing, setEditing] = useState<{ isNew: boolean; form: Form } | null>(null)
  const [removing, setRemoving] = useState<CatalogDye | null>(null)
  const [busy, setBusy] = useState(false)
  const [modalError, setModalError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    api.dyeCatalog().then(setData).catch(e => setLoadError(e instanceof Error ? e.message : 'Failed to load dyes'))
  }, [])

  if (loadError) return <p className="error-text">{loadError}</p>
  if (!data) return <p className="text-muted">Loading...</p>

  const openEdit = (d?: CatalogDye) => {
    setModalError(null)
    setEditing(d
      ? { isNew: false, form: { dye_id: d.dye_id, dye_name: d.dye_name, weight: String(d.weight), hex: d.hex, role_id: d.role_id ?? '', emoji_id: d.emoji_id ?? '' } }
      : { isNew: true, form: EMPTY })
  }
  const setField = (k: keyof Form, v: string) => setEditing(e => (e ? { ...e, form: { ...e.form, [k]: v } } : e))

  const others = editing ? data.dyes.filter(d => d.dye_id !== editing.form.dye_id).reduce((a, d) => a + d.weight, 0) : 0
  const err = editing ? formError(editing.form, editing.isNew, others) : null

  const save = async () => {
    if (!editing || err) return
    setBusy(true)
    setModalError(null)
    try {
      const f = editing.form
      setData(await api.saveDye(f.dye_id, {
        dye_name: f.dye_name.trim(), weight: Number(f.weight), hex: f.hex.trim().replace('#', ''),
        role_id: f.role_id.trim(), emoji_id: f.emoji_id.trim(),
      }))
      setNotice(`${editing.isNew ? 'Added' : 'Saved'} ${f.dye_name.trim()}.`)
      setEditing(null)
    } catch (e: unknown) {
      setModalError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setBusy(false)
    }
  }

  const remove = async () => {
    if (!removing) return
    setBusy(true)
    setModalError(null)
    try {
      const next = await api.deleteDye(removing.dye_id)
      setData(next)
      setNotice(`Removed ${removing.dye_name}${next.unlocks_removed ? ` and ${next.unlocks_removed} player unlock${next.unlocks_removed === 1 ? '' : 's'}` : ''}.`)
      setRemoving(null)
    } catch (e: unknown) {
      setModalError(e instanceof Error ? e.message : 'Remove failed')
    } finally {
      setBusy(false)
    }
  }

  const noDrop = Math.max(0, 100 - data.total_weight)
  return (
    <div className="card reveal" style={{ '--i': 3 } as React.CSSProperties}>
      <div className="card-head">
        <span className="card-title">Dye catalog</span>
        {canEdit && (
          <button className="btn btn-primary btn-sm" onClick={() => openEdit()} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <PlusIcon width={14} height={14} />Add dye
          </button>
        )}
      </div>
      <p className="card-sub" style={{ padding: '0 20px 10px' }}>
        Every guild chat message rolls for a dye. Weight is the percent chance per message, so a weight of 0.01 is 1 in 10,000.
        Together the weights cover {+data.total_weight.toFixed(4)}%; the other {+noDrop.toFixed(4)}% of messages drop nothing.
        The role is the Discord colour role /dyes gives; the emoji shows in its reply. Neither is required.
      </p>
      {notice && <p className="card-sub" style={{ padding: '0 20px 10px' }}><span className="badge badge-on">{notice}</span></p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Dye</th><th>Weight</th><th>Odds</th><th>Role</th><th>Emoji</th><th>Owned by</th>{canEdit && <th aria-label="Actions" />}</tr>
          </thead>
          <tbody>
            {data.dyes.map(d => (
              <tr key={d.dye_id}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ width: 14, height: 14, borderRadius: 4, background: `#${d.hex}`, flexShrink: 0, boxShadow: 'inset 0 0 0 1px var(--border-strong)' }} />
                    <div>
                      <div className="p-name">{d.dye_name}</div>
                      <div className="p-sub mono">{d.dye_id}</div>
                    </div>
                  </div>
                </td>
                <td className="num">{d.weight}</td>
                <td className="num">{d.odds}</td>
                <td>{d.role_id ? <span className="mono">{d.role_id}</span> : <span className="badge badge-warn">None</span>}</td>
                <td>{d.emoji_id ? <span title={d.emoji_id} style={{ display: 'inline-flex' }}><DyeEmoji id={d.emoji_id} /></span> : <span className="badge badge-warn">None</span>}</td>
                <td className="num">{d.unlocked_by}</td>
                {canEdit && (
                  <td style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
                    <button className="icon-btn sm" title={`Edit ${d.dye_name}`} aria-label={`Edit ${d.dye_name}`} onClick={() => openEdit(d)}><PencilIcon width={14} height={14} /></button>{' '}
                    <button className="icon-btn sm" title={`Remove ${d.dye_name}`} aria-label={`Remove ${d.dye_name}`} onClick={() => { setModalError(null); setRemoving(d) }}><TrashIcon width={14} height={14} /></button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <Modal
          title={editing.isNew ? 'Add dye' : `Edit ${editing.form.dye_name || editing.form.dye_id}`}
          onClose={() => setEditing(null)}
          error={modalError}
          actions={<>
            <button className="btn" onClick={() => setEditing(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={save} disabled={!!err || busy}>{busy ? 'Saving...' : editing.isNew ? 'Add dye' : 'Save'}</button>
          </>}
        >
          <div style={{ display: 'grid', gap: 12 }}>
            {editing.isNew && (
              <div>
                <label className="form-label" htmlFor="dye-id">ID</label>
                <input id="dye-id" className="form-input" style={{ width: '100%' }} placeholder="mango_dye" value={editing.form.dye_id}
                  onChange={e => setField('dye_id', e.target.value.toLowerCase())} />
              </div>
            )}
            <div>
              <label className="form-label" htmlFor="dye-name">Name</label>
              <input id="dye-name" className="form-input" style={{ width: '100%' }} placeholder="Mango Dye" value={editing.form.dye_name}
                onChange={e => setField('dye_name', e.target.value)} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label className="form-label" htmlFor="dye-weight">Weight (% per message)</label>
                <input id="dye-weight" className="form-input" style={{ width: '100%' }} inputMode="decimal" placeholder="0.01" value={editing.form.weight}
                  onChange={e => setField('weight', e.target.value)} />
                <div className="card-sub" style={{ marginTop: 4 }}>{Number(editing.form.weight) > 0 ? oddsFor(Number(editing.form.weight)) : ' '}</div>
              </div>
              <div>
                <label className="form-label" htmlFor="dye-hex">Colour (hex)</label>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 22, height: 22, borderRadius: 6, flexShrink: 0, boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                    background: /^#?[0-9a-fA-F]{6}$/.test(editing.form.hex.trim()) ? `#${editing.form.hex.trim().replace('#', '')}` : 'transparent' }} />
                  <input id="dye-hex" className="form-input" style={{ width: '100%' }} placeholder="FDBE02" value={editing.form.hex}
                    onChange={e => setField('hex', e.target.value)} />
                </span>
              </div>
            </div>
            <div>
              <label className="form-label" htmlFor="dye-role">Discord role ID</label>
              <input id="dye-role" className="form-input mono" style={{ width: '100%' }} inputMode="numeric" value={editing.form.role_id}
                onChange={e => setField('role_id', e.target.value)} />
            </div>
            <div>
              <div className="form-label">Emoji</div>
              <EmojiPicker value={editing.form.emoji_id} onChange={id => setField('emoji_id', id)}
                uploadName={editing.form.dye_id} canEdit={canEdit} />
            </div>
            <div className="card-sub">Without a role, players can still win the dye but /dyes can't give them its colour. Without an emoji, the /dyes reply just shows the name.</div>
            {err && <p className="error-text" style={{ margin: 0 }}>{err}</p>}
          </div>
        </Modal>
      )}

      {removing && (
        <Modal
          title={`Remove ${removing.dye_name}?`}
          onClose={() => setRemoving(null)}
          error={modalError}
          actions={<>
            <button className="btn" onClick={() => setRemoving(null)}>Cancel</button>
            <button className="btn btn-danger" onClick={remove} disabled={busy}>{busy ? 'Removing...' : 'Remove dye'}</button>
          </>}
        >
          <p>
            It stops dropping straight away
            {removing.unlocked_by > 0
              ? <>, and the <b>{removing.unlocked_by}</b> {removing.unlocked_by === 1 ? 'player who has' : 'players who have'} it lose it from their collection. This can't be undone.</>
              : '. Nobody has it yet.'}
          </p>
          <p className="card-sub">Anyone already wearing its Discord role keeps the role until they pick another dye.</p>
        </Modal>
      )}
    </div>
  )
}
