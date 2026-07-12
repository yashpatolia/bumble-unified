import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import type { DyeProfile, DyeSearchResult } from '../types'

export default function Dyes() {
  const navigate = useNavigate()
  const [profile, setProfile] = useState<DyeProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewingOther, setViewingOther] = useState(false)

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<DyeSearchResult[]>([])
  const [searching, setSearching] = useState(false)

  const loadMine = () => {
    setLoading(true)
    setError(null)
    setViewingOther(false)
    api.myDyes()
      .then(setProfile)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load dyes'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadMine() }, [])

  const runSearch = () => {
    const q = query.trim()
    if (!q) { setResults([]); return }
    setSearching(true)
    api.searchDyeUsers(q)
      .then(r => setResults(r.results))
      .catch(() => setResults([]))
      .finally(() => setSearching(false))
  }

  const viewUser = (uuid: string) => {
    setLoading(true)
    setError(null)
    setViewingOther(true)
    api.userDyes(uuid)
      .then(setProfile)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load dyes'))
      .finally(() => setLoading(false))
  }

  const dyes = profile?.dyes ?? []
  const unlockedCount = dyes.filter(d => d.unlocked).length
  const sorted = [...dyes].sort((a, b) => {
    if (a.unlocked !== b.unlocked) return a.unlocked ? -1 : 1
    return b.weight - a.weight
  })

  return (
    <div>
      <div className="header-row">
        <div className="page-title" style={{ marginBottom: 0 }}>
          Dyes
          {profile?.linked && (
            <span className="text-muted" style={{ fontSize: 14, fontWeight: 400, marginLeft: 10 }}>
              {unlockedCount}/{dyes.length} unlocked
            </span>
          )}
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate(-1)}>← Back</button>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            className="form-input"
            placeholder="Search by IGN..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') runSearch() }}
          />
          <button className="btn btn-ghost" onClick={runSearch} disabled={searching}>
            {searching ? 'Searching...' : 'Search'}
          </button>
          {viewingOther && (
            <button className="btn btn-ghost" onClick={loadMine}>My Dyes</button>
          )}
        </div>

        {results.length > 0 && (
          <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {results.map(r => (
              <div
                key={r.uuid}
                onClick={() => viewUser(r.uuid)}
                style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 8px', borderRadius: 8, cursor: 'pointer' }}
                className="dye-search-result"
              >
                <img className="hex-avatar" src={`https://mc-heads.net/avatar/${r.uuid}/28`} alt="" style={{ width: 28, height: 28 }} />
                <span style={{ fontWeight: 500 }}>{r.ign}</span>
                {r.discord_name && <span className="text-muted" style={{ fontSize: 12 }}>{r.discord_name}</span>}
                <span className="text-muted" style={{ fontSize: 12, marginLeft: 'auto' }}>{r.unlocked_count} unlocked</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <p style={{ color: 'var(--red)', marginBottom: 16 }}>{error}</p>}

      {loading ? (
        <p className="empty">Loading...</p>
      ) : !profile?.linked ? (
        <p className="empty">
          {viewingOther ? 'This player is not linked.' : 'Link your Discord account with /link in Discord to track your dyes.'}
        </p>
      ) : (
        <>
          <div className="events-section-label">
            {viewingOther ? `${profile.ign}'s Dyes` : 'My Dyes'}
          </div>
          <div className="dye-grid">
            {sorted.map(d => (
              <div key={d.dye_id} className={`dye-swatch${d.unlocked ? '' : ' locked'}`}>
                <div className="dye-swatch-color" style={{ background: `#${d.hex}` }} />
                <div className="dye-swatch-name">{d.unlocked ? '' : '🔒 '}{d.dye_name}</div>
                <div className="dye-swatch-odds">{d.odds}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
