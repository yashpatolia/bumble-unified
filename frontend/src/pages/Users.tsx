import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../App'
import { Modal } from '../components/Modal'
import { isValidDiscordId } from '../lib/validators'
import type { PanelUser } from '../types'

interface FormState {
  discord_id: string
  discord_name: string
  can_control_bots: boolean
  can_fetch_api: boolean
  can_manage_links: boolean
}

const defaultForm = (): FormState => ({ discord_id: '', discord_name: '', can_control_bots: false, can_fetch_api: false, can_manage_links: false })

export default function Users() {
  const { me } = useAuth()
  const [users, setUsers] = useState<PanelUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editTarget, setEditTarget] = useState<PanelUser | null>(null)
  const [form, setForm] = useState<FormState>(defaultForm())
  const [saving, setSaving] = useState(false)

  const load = () =>
    api.users()
      .then(setUsers)
      .catch(() => setError('Failed to load users'))
      .finally(() => setLoading(false))

  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditTarget(null)
    setForm(defaultForm())
    setError(null)
    setShowModal(true)
  }

  const openEdit = (u: PanelUser) => {
    setEditTarget(u)
    setForm({ discord_id: String(u.discord_id), discord_name: u.discord_name, can_control_bots: u.can_control_bots, can_fetch_api: u.can_fetch_api, can_manage_links: u.can_manage_links })
    setError(null)
    setShowModal(true)
  }

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      if (editTarget) {
        await api.updateUser(editTarget.discord_id, { can_control_bots: form.can_control_bots, can_fetch_api: form.can_fetch_api, can_manage_links: form.can_manage_links })
      } else {
        if (!isValidDiscordId(form.discord_id.trim())) { setError('Invalid Discord ID'); return }
        await api.createUser({ discord_id: form.discord_id.trim(), discord_name: form.discord_name.trim() || 'Unknown', is_admin: false, can_control_bots: form.can_control_bots, can_fetch_api: form.can_fetch_api, can_manage_links: form.can_manage_links })
      }
      setShowModal(false)
      load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (u: PanelUser) => {
    if (!confirm(`Remove ${u.discord_name} from the panel?`)) return
    try {
      await api.deleteUser(u.discord_id)
      load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  return (
    <div>
      <div className="header-row">
        <div className="page-title" style={{ marginBottom: 0 }}>Panel Users</div>
        <button className="btn btn-primary" onClick={openCreate}>+ Add User</button>
      </div>

      {error && <p style={{ color: 'var(--red)', marginBottom: 16 }}>{error}</p>}

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          {loading ? (
            <p className="empty">Loading...</p>
          ) : users.length === 0 ? (
            <p className="empty">No users yet.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Discord Name</th>
                  <th>Discord ID</th>
                  <th>Permissions</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.discord_id}>
                    <td>{u.discord_name}</td>
                    <td className="mono" style={{ color: 'var(--muted)' }}>{u.discord_id}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {u.is_owner && <span className="badge badge-admin">Owner</span>}
                        {u.can_control_bots && <span className="badge badge-on">Control Bots</span>}
                        {u.can_fetch_api && <span className="badge badge-on">API Fetching</span>}
                        {u.can_manage_links && <span className="badge badge-on">Manage Links</span>}
                        {!u.is_owner && !u.can_control_bots && !u.can_fetch_api && !u.can_manage_links && <span className="badge badge-off">None</span>}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn btn-ghost" style={{ padding: '4px 10px' }} onClick={() => openEdit(u)}>Edit</button>
                        {String(u.discord_id) !== me?.discord_id && (
                          <button className="btn btn-danger" style={{ padding: '4px 10px' }} onClick={() => remove(u)}>Remove</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {showModal && (
        <Modal
          title={editTarget ? 'Edit User' : 'Add User'}
          onClose={() => setShowModal(false)}
          error={error}
          actions={<>
            <button className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={save} disabled={saving}>
              {saving ? 'Saving...' : 'Save'}
            </button>
          </>}
        >
          {!editTarget && (
            <>
              <div className="form-group">
                <label className="form-label">Discord User ID</label>
                <input
                  className="form-input"
                  placeholder="123456789012345678"
                  value={form.discord_id}
                  onChange={e => setForm(f => ({ ...f, discord_id: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Display Name</label>
                <input
                  className="form-input"
                  placeholder="Their Discord username"
                  value={form.discord_name}
                  onChange={e => setForm(f => ({ ...f, discord_name: e.target.value }))}
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label className="form-label">Permissions</label>
            <div className="toggle-row">
              <label htmlFor="perm-bots">Control Bots (start/stop/restart)</label>
              <input
                id="perm-bots"
                type="checkbox"
                checked={form.can_control_bots}
                onChange={e => setForm(f => ({ ...f, can_control_bots: e.target.checked }))}
              />
            </div>
            <div className="toggle-row">
              <label htmlFor="perm-fetch">API Fetching (Skyblock stats)</label>
              <input
                id="perm-fetch"
                type="checkbox"
                checked={form.can_fetch_api}
                onChange={e => setForm(f => ({ ...f, can_fetch_api: e.target.checked }))}
              />
            </div>
            <div className="toggle-row">
              <label htmlFor="perm-links">Manage Links (link/unlink members)</label>
              <input
                id="perm-links"
                type="checkbox"
                checked={form.can_manage_links}
                onChange={e => setForm(f => ({ ...f, can_manage_links: e.target.checked }))}
              />
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

