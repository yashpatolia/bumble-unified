import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../App'
import { DyeCatalogCard } from '../components/DyeCatalogCard'
import { SharedSettingsCard } from '../components/SharedSettingsCard'

type Tab = 'bot' | 'dyes'

const TABS: { id: Tab; label: string }[] = [
  { id: 'bot', label: 'Warpout and chat' },
  { id: 'dyes', label: 'Dyes' },
]

/** Settings that apply to both guilds (and the Discord server), so they live here instead of
 * being repeated under each guild's Config page. Each card saves on its own. */
export default function GlobalSettings() {
  const { me } = useAuth()
  const canEdit = !!(me?.can_manage_config || me?.is_admin || me?.is_owner)
  const [params, setParams] = useSearchParams()
  const tab: Tab = TABS.some(t => t.id === params.get('tab')) ? params.get('tab') as Tab : 'bot'

  return (
    <div>
      <div className="crumb reveal">Tools / Global settings</div>
      <div className="page-head reveal" style={{ '--i': 1 } as React.CSSProperties}>
        <h1 className="page-title">Global settings</h1>
      </div>
      <p className="card-sub reveal" style={{ '--i': 1, marginBottom: 14 } as React.CSSProperties}>
        These apply to both guilds and the Discord server. Rank requirements, activity tiers and each bot's Minecraft version are per guild, on its Config page.
      </p>

      {!canEdit && (
        <p className="badge badge-off" style={{ marginBottom: 14, whiteSpace: 'normal' }}>
          You can view these settings. Changing them needs the Manage Config permission.
        </p>
      )}

      <div className="tabs reveal" role="tablist" style={{ '--i': 2, marginBottom: 18, flexWrap: 'wrap' } as React.CSSProperties}>
        {TABS.map(t => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} className={`tab${tab === t.id ? ' active' : ''}`}
            onClick={() => setParams(p => { p.set('tab', t.id); return p }, { replace: true })}>{t.label}</button>
        ))}
      </div>

      {tab === 'bot' && <SharedSettingsCard canEdit={canEdit} />}
      {tab === 'dyes' && (
        <>
          <p className="card-sub" style={{ marginBottom: 12 }}>Each dye change saves straight away.</p>
          <DyeCatalogCard canEdit={canEdit} />
        </>
      )}
    </div>
  )
}
