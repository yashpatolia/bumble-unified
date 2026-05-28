import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'
import type { BingoEvent, BingoLeaderboardEntry, BingoTask } from '../types'

// ── Countdown ────────────────────────────────────────────────────────────────

function useCountdown(target: string | null) {
  const [diff, setDiff] = useState<number | null>(null)
  useEffect(() => {
    if (!target) { setDiff(null); return }
    const tick = () => setDiff(Math.max(0, new Date(target).getTime() - Date.now()))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [target])
  return diff
}

function formatCountdown(ms: number) {
  const s = Math.floor(ms / 1000)
  const days = Math.floor(s / 86400)
  const hours = Math.floor((s % 86400) / 3600)
  const mins = Math.floor((s % 3600) / 60)
  const secs = s % 60
  if (days > 0) return `${days}d ${String(hours).padStart(2, '0')}h ${String(mins).padStart(2, '0')}m`
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

function Countdown({ event }: { event: BingoEvent }) {
  const startMs = useCountdown(event.status === 'draft' ? event.starts_at : null)
  const endMs = useCountdown(event.status === 'active' ? event.ends_at : null)
  const ms = event.status === 'active' ? endMs : startMs

  if (event.status === 'ended') {
    return <div className="bingo-countdown-ended">Event has ended</div>
  }
  if (ms === null) return null
  return (
    <div style={{ textAlign: 'center' }}>
      <div className="bingo-countdown">{ms === 0 ? '—' : formatCountdown(ms)}</div>
      <div className="bingo-countdown-label">
        {event.status === 'active' ? 'Time remaining' : 'Starts in'}
      </div>
    </div>
  )
}

// ── Bingo cell ────────────────────────────────────────────────────────────────

const DIFF_COLORS: Record<string, string> = { easy: 'easy', medium: 'medium', hard: 'hard' }

function BingoCell({
  position, task, onClick,
}: {
  position: number
  task: BingoTask | undefined
  onClick?: (pos: number) => void
}) {
  if (position === 12) {
    return (
      <div className="bingo-cell free">
        <div className="bingo-cell-free-label">FREE</div>
      </div>
    )
  }

  const classes = [
    'bingo-cell',
    onClick ? 'clickable' : '',
    !task ? 'empty' : '',
  ].filter(Boolean).join(' ')

  if (!task) {
    return (
      <div className={classes} onClick={() => onClick?.(position)}>
        <div className="bingo-cell-name" style={{ color: 'var(--muted)' }}>Empty</div>
      </div>
    )
  }

  const targetAmt = (task.target as Record<string, number>).amount ?? null

  return (
    <div className={classes} onClick={() => onClick?.(position)}>
      {task.difficulty && (
        <span className={`bingo-cell-diff ${DIFF_COLORS[task.difficulty] ?? ''}`} />
      )}
      <div className="bingo-cell-name">{task.name}</div>
      {targetAmt !== null && (
        <div className="bingo-cell-progress">Goal: {targetAmt.toLocaleString()}</div>
      )}
    </div>
  )
}

// ── Task edit modal ───────────────────────────────────────────────────────────

const TASK_TYPES = [
  { value: 'skill_xp', label: 'Skill XP' },
  { value: 'slayer_tier', label: 'Slayer Completions' },
  { value: 'dungeon_xp', label: 'Dungeon XP' },
  { value: 'collection', label: 'Collection' },
]

const SKILLS = ['farming', 'mining', 'combat', 'foraging', 'fishing', 'enchanting', 'alchemy', 'carpentry', 'taming']
const SLAYERS = ['zombie', 'spider', 'wolf', 'enderman', 'blaze', 'vampire']

interface TaskForm {
  name: string
  description: string
  task_type: string
  difficulty: string
  amount: string
  skill: string
  slayer: string
  slayer_tier: string
  collection_item: string
}

const defaultTaskForm = (): TaskForm => ({
  name: '', description: '', task_type: 'skill_xp', difficulty: 'medium',
  amount: '', skill: 'farming', slayer: 'zombie', slayer_tier: '1', collection_item: '',
})

function taskToForm(t: BingoTask): TaskForm {
  const tgt = t.target as Record<string, unknown>
  return {
    name: t.name, description: t.description,
    task_type: t.task_type, difficulty: t.difficulty,
    amount: String(tgt.amount ?? ''),
    skill: String(tgt.skill ?? 'farming'),
    slayer: String(tgt.slayer ?? 'zombie'),
    slayer_tier: String(tgt.tier ?? 1),
    collection_item: String(tgt.item ?? ''),
  }
}

function buildTarget(form: TaskForm): Record<string, unknown> {
  switch (form.task_type) {
    case 'skill_xp':    return { skill: form.skill, amount: Number(form.amount) }
    case 'slayer_tier': return { slayer: form.slayer, tier: Number(form.slayer_tier), amount: Number(form.amount) }
    case 'dungeon_xp':  return { amount: Number(form.amount) }
    case 'collection':  return { item: form.collection_item.toUpperCase().replace(/ /g, '_'), amount: Number(form.amount) }
    default:            return { amount: Number(form.amount) }
  }
}

function TaskModal({
  position, existing, slug, onClose, onSaved,
}: {
  position: number
  existing: BingoTask | undefined
  slug: string
  onClose: () => void
  onSaved: () => void
}) {
  const [form, setForm] = useState<TaskForm>(existing ? taskToForm(existing) : defaultTaskForm())
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const set = (patch: Partial<TaskForm>) => setForm(f => ({ ...f, ...patch }))

  const save = async () => {
    if (!form.name.trim()) { setError('Name is required'); return }
    setSaving(true); setError(null)
    try {
      await api.upsertBingoTask(slug, position, {
        name: form.name.trim(),
        description: form.description.trim(),
        task_type: form.task_type,
        target: buildTarget(form),
        difficulty: form.difficulty,
      })
      onSaved()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const del = async () => {
    if (!existing) return
    setDeleting(true); setError(null)
    try {
      await api.deleteBingoTask(slug, position)
      onSaved()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal" style={{ width: 480 }}>
        <div className="modal-title">Square {position + 1} — {existing ? 'Edit Task' : 'Add Task'}</div>
        {error && <p style={{ color: 'var(--red)', marginBottom: 12, fontSize: 13 }}>{error}</p>}

        <div className="form-group">
          <label className="form-label">Task Name</label>
          <input className="form-input" value={form.name} onChange={e => set({ name: e.target.value })} placeholder="e.g. Gain Farming XP" />
        </div>
        <div className="form-group">
          <label className="form-label">Description (optional)</label>
          <input className="form-input" value={form.description} onChange={e => set({ description: e.target.value })} placeholder="Short description shown on hover" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="form-group">
            <label className="form-label">Task Type</label>
            <select className="form-input" value={form.task_type} onChange={e => set({ task_type: e.target.value })}>
              {TASK_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Difficulty</label>
            <select className="form-input" value={form.difficulty} onChange={e => set({ difficulty: e.target.value })}>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>

        {form.task_type === 'skill_xp' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Skill</label>
              <select className="form-input" value={form.skill} onChange={e => set({ skill: e.target.value })}>
                {SKILLS.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">XP Amount</label>
              <input className="form-input" type="number" value={form.amount} onChange={e => set({ amount: e.target.value })} placeholder="e.g. 100000" />
            </div>
          </div>
        )}

        {form.task_type === 'slayer_tier' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Slayer</label>
              <select className="form-input" value={form.slayer} onChange={e => set({ slayer: e.target.value })}>
                {SLAYERS.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Tier</label>
              <select className="form-input" value={form.slayer_tier} onChange={e => set({ slayer_tier: e.target.value })}>
                {[1,2,3,4].map(t => <option key={t} value={t}>T{t}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Count</label>
              <input className="form-input" type="number" value={form.amount} onChange={e => set({ amount: e.target.value })} placeholder="e.g. 5" />
            </div>
          </div>
        )}

        {form.task_type === 'dungeon_xp' && (
          <div className="form-group">
            <label className="form-label">Dungeon XP Amount</label>
            <input className="form-input" type="number" value={form.amount} onChange={e => set({ amount: e.target.value })} placeholder="e.g. 50000" />
          </div>
        )}

        {form.task_type === 'collection' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Item ID</label>
              <input className="form-input" value={form.collection_item} onChange={e => set({ collection_item: e.target.value })} placeholder="e.g. WHEAT or Sugar Cane" />
            </div>
            <div className="form-group">
              <label className="form-label">Amount</label>
              <input className="form-input" type="number" value={form.amount} onChange={e => set({ amount: e.target.value })} placeholder="e.g. 10000" />
            </div>
          </div>
        )}

        <div className="modal-actions">
          {existing && (
            <button className="btn btn-danger" onClick={del} disabled={deleting} style={{ marginRight: 'auto' }}>
              {deleting ? 'Removing...' : 'Remove'}
            </button>
          )}
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {saving ? 'Saving...' : 'Save Task'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── New event form ────────────────────────────────────────────────────────────

const MODE_OPTIONS = [
  { value: 'individual', label: 'Individual' },
  { value: 'team', label: 'Team' },
  { value: 'combined_shared', label: 'Combined — Shared Card' },
  { value: 'combined_versus', label: 'BK vs BU' },
  { value: 'combined_individual', label: 'Combined — Individual' },
]

interface EventForm {
  slug: string; name: string; mode: string
  guilds: string[]; starts_at: string; ends_at: string
}

const defaultEventForm = (): EventForm => ({
  slug: '', name: '', mode: 'individual', guilds: [], starts_at: '', ends_at: '',
})

function NewEventPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<EventForm>(defaultEventForm())
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const set = (patch: Partial<EventForm>) => setForm(f => ({ ...f, ...patch }))

  const toggleGuild = (g: string) =>
    set({ guilds: form.guilds.includes(g) ? form.guilds.filter(x => x !== g) : [...form.guilds, g] })

  const save = async () => {
    if (!form.slug.trim() || !form.name.trim()) { setError('Slug and name are required'); return }
    if (form.guilds.length === 0) { setError('Select at least one guild'); return }
    if (!form.starts_at || !form.ends_at) { setError('Start and end dates are required'); return }
    setSaving(true); setError(null)
    try {
      const r = await api.createEvent({
        slug: form.slug.trim(),
        name: form.name.trim(),
        mode: form.mode,
        guilds: form.guilds,
        starts_at: new Date(form.starts_at).toISOString(),
        ends_at: new Date(form.ends_at).toISOString(),
      })
      navigate(`/events/${r.slug}`)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create event')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="home-page">
      <header className="home-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span className="guild-header-back" onClick={() => navigate('/events')}>← Events</span>
          <span className="guild-header-sep">/</span>
          <div className="home-logo" style={{ fontSize: 14, fontWeight: 600 }}>New Event</div>
        </div>
      </header>
      <div className="home-body">
        <div className="home-title" style={{ marginBottom: 24 }}>Create Event</div>

        {error && <p style={{ color: 'var(--red)', marginBottom: 16 }}>{error}</p>}

        <div className="card" style={{ maxWidth: 560 }}>
          <div className="form-group">
            <label className="form-label">Event Name</label>
            <input className="form-input" value={form.name} onChange={e => set({ name: e.target.value })} placeholder="e.g. Summer Bingo 2025" />
          </div>
          <div className="form-group">
            <label className="form-label">Slug (URL identifier)</label>
            <input className="form-input" value={form.slug} onChange={e => set({ slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') })} placeholder="e.g. summer-bingo-2025" />
          </div>
          <div className="form-group">
            <label className="form-label">Mode</label>
            <select className="form-input" value={form.mode} onChange={e => set({ mode: e.target.value })}>
              {MODE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Guilds</label>
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              {['bk', 'bu'].map(g => (
                <button
                  key={g}
                  type="button"
                  className={form.guilds.includes(g) ? 'btn btn-primary' : 'btn btn-ghost'}
                  onClick={() => toggleGuild(g)}
                >
                  {g.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Starts At</label>
              <input className="form-input" type="datetime-local" value={form.starts_at} onChange={e => set({ starts_at: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Ends At</label>
              <input className="form-input" type="datetime-local" value={form.ends_at} onChange={e => set({ ends_at: e.target.value })} />
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
            <button className="btn btn-ghost" onClick={() => navigate('/events')}>Cancel</button>
            <button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? 'Creating...' : 'Create Event'}</button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Leaderboard tab ───────────────────────────────────────────────────────────

function LeaderboardTab({ slug }: { slug: string }) {
  const [rows, setRows] = useState<BingoLeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getEventLeaderboard(slug)
      .then(r => setRows(r.leaderboard))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [slug])

  if (loading) return <p className="empty">Loading...</p>
  if (rows.length === 0) return <p className="empty">No progress recorded yet.</p>

  const GUILD_LABELS: Record<string, string> = { bk: 'BK', bu: 'BU' }

  return (
    <div className="card" style={{ padding: 0 }}>
      {rows.map((r, i) => (
        <div key={r.uuid} className="bingo-lb-row">
          <div className="bingo-lb-rank">#{i + 1}</div>
          {r.discord_avatar ? (
            <img src={r.discord_avatar} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
          ) : (
            <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--surface3)' }} />
          )}
          <div className="bingo-lb-name">
            {r.ign ?? 'Unknown'}
            {r.discord_name && (
              <span style={{ color: 'var(--muted)', fontWeight: 400, marginLeft: 6, fontSize: 12 }}>
                {r.discord_name}
              </span>
            )}
          </div>
          {r.guild_key && (
            <span className="badge badge-warn" style={{ fontSize: 10 }}>{GUILD_LABELS[r.guild_key] ?? r.guild_key}</span>
          )}
          {r.blackout && <span className="badge badge-on" style={{ fontSize: 10 }}>BLACKOUT</span>}
          <div className="bingo-lb-count">{r.completed_count}/24</div>
        </div>
      ))}
    </div>
  )
}

// ── Event settings modal ──────────────────────────────────────────────────────

function EditSettingsModal({
  event, slug, onClose, onSaved,
}: {
  event: BingoEvent; slug: string; onClose: () => void; onSaved: () => void
}) {
  const toLocal = (iso: string | null) => iso ? iso.slice(0, 16) : ''
  const [form, setForm] = useState({
    name: event.name,
    mode: event.mode,
    guilds: [...event.guilds],
    starts_at: toLocal(event.starts_at),
    ends_at: toLocal(event.ends_at),
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const set = (patch: Partial<typeof form>) => setForm(f => ({ ...f, ...patch }))

  const toggleGuild = (g: string) =>
    set({ guilds: form.guilds.includes(g) ? form.guilds.filter(x => x !== g) : [...form.guilds, g] })

  const save = async () => {
    setSaving(true); setError(null)
    try {
      await api.updateEvent(slug, {
        name: form.name, mode: form.mode, guilds: form.guilds,
        starts_at: new Date(form.starts_at).toISOString(),
        ends_at: new Date(form.ends_at).toISOString(),
      })
      onSaved()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal" style={{ width: 480 }}>
        <div className="modal-title">Event Settings</div>
        {error && <p style={{ color: 'var(--red)', marginBottom: 12, fontSize: 13 }}>{error}</p>}
        <div className="form-group">
          <label className="form-label">Event Name</label>
          <input className="form-input" value={form.name} onChange={e => set({ name: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="form-label">Mode</label>
          <select className="form-input" value={form.mode} onChange={e => set({ mode: e.target.value })}>
            {MODE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Guilds</label>
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            {['bk', 'bu'].map(g => (
              <button key={g} type="button"
                className={form.guilds.includes(g) ? 'btn btn-primary' : 'btn btn-ghost'}
                onClick={() => toggleGuild(g)}
              >{g.toUpperCase()}</button>
            ))}
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="form-group">
            <label className="form-label">Starts At</label>
            <input className="form-input" type="datetime-local" value={form.starts_at} onChange={e => set({ starts_at: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">Ends At</label>
            <input className="form-input" type="datetime-local" value={form.ends_at} onChange={e => set({ ends_at: e.target.value })} />
          </div>
        </div>
        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
        </div>
      </div>
    </div>
  )
}

// ── Main event page ───────────────────────────────────────────────────────────

const MODE_LABELS: Record<string, string> = {
  individual: 'Individual',
  team: 'Team',
  combined_shared: 'Shared Card',
  combined_versus: 'BK vs BU',
  combined_individual: 'Combined Individual',
}

const GUILD_LABELS: Record<string, string> = { bk: 'BK', bu: 'BU' }

export default function EventsBingo() {
  const { slug } = useParams<{ slug: string }>()
  if (!slug) return <NewEventPage />
  return <EventBingoInner slug={slug} />
}

type Tab = 'card' | 'leaderboard'

function EventBingoInner({ slug }: { slug: string }) {
  const navigate = useNavigate()
  const { me } = useAuth()
  const isManager = me?.can_manage_events || me?.is_admin || false

  const [event, setEvent] = useState<BingoEvent | null>(null)
  const [tasks, setTasks] = useState<BingoTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('card')
  const [editCell, setEditCell] = useState<number | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [statusBusy, setStatusBusy] = useState(false)
  const [statusError, setStatusError] = useState<string | null>(null)

  const load = () => {
    api.getEvent(slug)
      .then(r => { setEvent(r.event); setTasks(r.tasks) })
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load event'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [slug])

  const setStatus = async (status: string) => {
    if (!event) return
    setStatusBusy(true); setStatusError(null)
    try {
      await api.setEventStatus(slug, status)
      load()
    } catch (e: unknown) {
      setStatusError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setStatusBusy(false)
    }
  }

  const filledCount = tasks.filter(t => t.task_type !== 'free').length

  if (loading) {
    return (
      <div className="home-page">
        <header className="home-header">
          <span className="guild-header-back" onClick={() => navigate('/events')}>← Events</span>
        </header>
        <div className="home-body"><p className="empty">Loading...</p></div>
      </div>
    )
  }

  if (error || !event) {
    return (
      <div className="home-page">
        <header className="home-header">
          <span className="guild-header-back" onClick={() => navigate('/events')}>← Events</span>
        </header>
        <div className="home-body">
          <p className="empty">{error ?? 'Event not found'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="home-page">
      <header className="home-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span className="guild-header-back" onClick={() => navigate('/events')}>← Events</span>
          <span className="guild-header-sep">/</span>
          <div className="home-logo" style={{ fontSize: 14, fontWeight: 600 }}>{event.name}</div>
        </div>
        <div className="home-user">
          {me?.avatar_url && (
            <img src={me.avatar_url} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
          )}
          <span>{me?.discord_name}</span>
          {me?.is_owner && (
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/users')}>Admin</button>
          )}
        </div>
      </header>

      <div className="home-body" style={{ maxWidth: 960 }}>
        {/* Event header row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 24, marginBottom: 32, flexWrap: 'wrap' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.04em', margin: 0 }}>{event.name}</h1>
              {event.status === 'active' && <span className="badge badge-on">Active</span>}
              {event.status === 'draft' && <span className="badge badge-warn">Draft</span>}
              {event.status === 'ended' && <span className="badge badge-off">Ended</span>}
            </div>
            <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
              {event.guilds.map(g => (
                <span key={g} className="badge badge-warn" style={{ fontSize: 10 }}>{GUILD_LABELS[g] ?? g.toUpperCase()}</span>
              ))}
              <span className="badge badge-user" style={{ fontSize: 10 }}>{MODE_LABELS[event.mode] ?? event.mode}</span>
              {isManager && event.status === 'draft' && (
                <span className="badge badge-user" style={{ fontSize: 10 }}>{filledCount}/24 tasks set</span>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
            <Countdown event={event} />
            {isManager && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                {event.status !== 'active' && (
                  <button className="btn btn-ghost btn-sm" onClick={() => setShowSettings(true)}>Settings</button>
                )}
                {event.status === 'draft' && (
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => setStatus('active')}
                    disabled={statusBusy || filledCount < 24}
                    title={filledCount < 24 ? `Fill all 24 tasks first (${filledCount}/24)` : ''}
                  >
                    {statusBusy ? '...' : 'Activate'}
                  </button>
                )}
                {event.status === 'active' && (
                  <button className="btn btn-danger btn-sm" onClick={() => setStatus('ended')} disabled={statusBusy}>
                    {statusBusy ? '...' : 'End Event'}
                  </button>
                )}
                {event.status === 'ended' && (
                  <button className="btn btn-ghost btn-sm" onClick={() => setStatus('draft')} disabled={statusBusy}>
                    {statusBusy ? '...' : 'Revert to Draft'}
                  </button>
                )}
              </div>
            )}
            {statusError && <p style={{ color: 'var(--red)', fontSize: 12, margin: 0 }}>{statusError}</p>}
          </div>
        </div>

        {/* Tabs — only show for non-draft or managers */}
        {(event.status !== 'draft' || isManager) && (
          <div className="bingo-tabs">
            <button className={`bingo-tab ${tab === 'card' ? 'active' : ''}`} onClick={() => setTab('card')}>
              Bingo Card
            </button>
            <button className={`bingo-tab ${tab === 'leaderboard' ? 'active' : ''}`} onClick={() => setTab('leaderboard')}>
              Leaderboard
            </button>
          </div>
        )}

        {/* Card tab */}
        {tab === 'card' && (
          <>
            {event.status === 'draft' && isManager && (
              <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 20 }}>
                Click any square to add or edit a task. The center square is always a Free Space.
              </p>
            )}
            <div className="bingo-grid">
              {Array.from({ length: 25 }, (_, i) => {
                const task = tasks.find(t => t.position === i)
                return (
                  <BingoCell
                    key={i}
                    position={i}
                    task={task}
                    onClick={isManager && event.status === 'draft' ? pos => setEditCell(pos) : undefined}
                  />
                )
              })}
            </div>
          </>
        )}

        {/* Leaderboard tab */}
        {tab === 'leaderboard' && <LeaderboardTab slug={slug} />}
      </div>

      {editCell !== null && (
        <TaskModal
          position={editCell}
          existing={tasks.find(t => t.position === editCell)}
          slug={slug}
          onClose={() => setEditCell(null)}
          onSaved={() => { setEditCell(null); load() }}
        />
      )}

      {showSettings && (
        <EditSettingsModal
          event={event}
          slug={slug}
          onClose={() => setShowSettings(false)}
          onSaved={() => { setShowSettings(false); load() }}
        />
      )}
    </div>
  )
}
