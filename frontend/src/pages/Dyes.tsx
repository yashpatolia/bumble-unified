import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { formatRelativeTime } from '../lib/time'
import type { DyeDrop, DyeProfile, DyeSearchResult } from '../types'

function dyeIconUrl(dyeName: string): string {
  return `https://hypixelskyblock.minecraft.wiki/images/${dyeName.replace(/ /g, '_')}.png`
}

function timeAgo(iso: string): string {
  return formatRelativeTime(Date.now() - new Date(iso).getTime(), { justNowUnderMins: 1 })
}

export default function Dyes() {
  const navigate = useNavigate()
  const [profile, setProfile] = useState<DyeProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewingOther, setViewingOther] = useState(false)

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<DyeSearchResult[]>([])
  const [searching, setSearching] = useState(false)

  const [recent, setRecent] = useState<DyeDrop[]>([])

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

  useEffect(() => {
    api.recentDyeDrops().then(r => setRecent(r.drops)).catch(() => {})
  }, [])

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
      <div className="crumb reveal">Tools / Dyes</div>
      <div className="page-head reveal" style={{ '--i': 1 } as React.CSSProperties}>
        <h1 className="page-title">
          Dyes
          {profile?.linked && <small>{unlockedCount} of {dyes.length} unlocked</small>}
        </h1>
        <button className="btn btn-sm" onClick={() => navigate(-1)}>Back</button>
      </div>

      <div className="card card-pad reveal" style={{ marginBottom: 16, '--i': 2 } as React.CSSProperties}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            className="form-input"
            placeholder="Search by IGN..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') runSearch() }}
          />
          <button className="btn" onClick={runSearch} disabled={searching}>
            {searching ? 'Searching...' : 'Search'}
          </button>
          {viewingOther && (
            <button className="btn" onClick={loadMine}>My dyes</button>
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
                <img src={`https://mc-heads.net/avatar/${r.uuid}/28`} alt="" width={28} height={28} style={{ borderRadius: 7 }} />
                <span style={{ fontWeight: 500 }}>{r.ign}</span>
                {r.discord_name && <span className="text-muted" style={{ fontSize: 12 }}>{r.discord_name}</span>}
                <span className="text-muted" style={{ fontSize: 12, marginLeft: 'auto' }}>{r.unlocked_count} unlocked</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {recent.length > 0 && (
        <div className="card card-pad reveal" style={{ marginBottom: 16, '--i': 3 } as React.CSSProperties}>
          <div className="card-title" style={{ marginBottom: 8 }}>Recently dropped</div>
          <div>
            {recent.map((d, i) => (
              <div key={i} className="dye-recent-row">
                <img src={`https://mc-heads.net/avatar/${d.uuid}/26`} alt="" width={26} height={26} style={{ borderRadius: 7 }} />
                <span style={{ fontWeight: 500, fontSize: 13 }}>{d.ign}</span>
                <span className="text-muted" style={{ fontSize: 12 }}>found</span>
                <div className="dye-recent-icon-frame" style={{ background: `#${d.hex}33` }}>
                  <img className="dye-recent-icon" src={dyeIconUrl(d.dye_name)} alt="" />
                </div>
                <span style={{ fontSize: 13, fontWeight: 500 }}>{d.dye_name}</span>
                <span className="dye-recent-time">{timeAgo(d.unlocked_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}

      {loading ? (
        <p className="empty">Loading...</p>
      ) : !profile?.linked ? (
        <p className="empty">
          {viewingOther ? 'This player is not linked.' : 'Search for a player above to see their dyes. Sign in and link your account with /link in Discord to track your own.'}
        </p>
      ) : (
        <>
          <div className="section-label">{viewingOther ? `${profile.ign}'s dyes` : 'My dyes'}</div>
          <div className="dye-grid">
            {sorted.map(d => (
              <div key={d.dye_id} className={`dye-swatch${d.unlocked ? '' : ' locked'}`} title={d.unlocked ? undefined : 'Not unlocked yet'}>
                <div className="dye-icon-frame" style={{ background: `#${d.hex}33` }}>
                  <img className="dye-icon" src={dyeIconUrl(d.dye_name)} alt="" />
                </div>
                <div className="dye-swatch-name">{d.dye_name}</div>
                <div className="dye-swatch-odds">{d.odds}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
