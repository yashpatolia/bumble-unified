import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../App'
import type { PanelUser } from '../types'

interface FormState {
  discord_id: string
  discord_name: string
  is_admin: boolean
  can_view_logs: boolean
}

const defaultForm = (): FormState => ({ discord_id: '', discord_name: '', is_admin: false, can_view_logs: true })

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
    setForm({ discord_id: String(u.discord_id), discord_name: u.discord_name, is_admin: u.is_admin, can_view_logs: u.can_view_logs })
    setError(null)
    setShowModal(true)
  }

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      if (editTarget) {
        await api.updateUser(editTarget.discord_id, { is_admin: form.is_admin, can_view_logs: form.can_view_logs })
      } else {
        const id = parseInt(form.discord_id)
        if (!id || isNaN(id)) { setError('Invalid Discord ID'); return }
        await api.createUser({ discord_id: id, discord_name: form.discord_name.trim() || 'Unknown', is_admin: form.is_admin, can_view_logs: form.can_view_logs })
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
        <div className="page-title" style={{ marginBottom: 0 }}>Users</div>
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
                  <th>Role</th>
                  <th>View Logs</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.discord_id}>
                    <td>{u.discord_name}</td>
                    <td style={{ color: 'var(--muted)', fontFamily: 'monospace' }}>{u.discord_id}</td>
                    <td>
                      <span className={`badge ${u.is_admin ? 'badge-admin' : 'badge-user'}`}>
                        {u.is_admin ? 'Admin' : 'User'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${u.can_view_logs ? 'badge-on' : 'badge-off'}`}>
                        {u.can_view_logs ? 'Yes' : 'No'}
                      </span>
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
        <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) setShowModal(false) }}>
          <div className="modal">
            <div className="modal-title">{editTarget ? 'Edit User' : 'Add User'}</div>
            {error && <p style={{ color: 'var(--red)', marginBottom: 12, fontSize: 13 }}>{error}</p>}

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
                <label htmlFor="perm-logs">View Logs</label>
                <input
                  id="perm-logs"
                  type="checkbox"
                  checked={form.can_view_logs}
                  onChange={e => setForm(f => ({ ...f, can_view_logs: e.target.checked }))}
                />
              </div>
              <div className="toggle-row">
                <label htmlFor="perm-admin">Admin (full access)</label>
                <input
                  id="perm-admin"
                  type="checkbox"
                  checked={form.is_admin}
                  onChange={e => setForm(f => ({ ...f, is_admin: e.target.checked }))}
                />
              </div>
            </div>

            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={save} disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
