import { ActivityChart } from '../components/ActivityChart'
import { ArrowRightIcon, CheckCircleIcon, TrophyIcon, UsersIcon, BotIcon } from '../components/icons'
import { GuestButton } from '../components/GuestButton'
import { ThemeToggle } from '../components/ThemeToggle'
import type { ActivityPoint } from '../types'

// Sample numbers for the product preview only; nothing here is real guild data.
const SAMPLE_ONLINE = [12, 9, 7, 5, 4, 6, 10, 15, 19, 22, 24, 27, 30, 34, 38, 41, 46, 52, 61, 58, 49, 38, 27, 18]
const samplePoints = (): ActivityPoint[] =>
  SAMPLE_ONLINE.map((online, i) => ({ t: new Date(Date.now() - (23 - i) * 3600000).toISOString(), online }))

const PREVIEW_ATTENTION = [
  { n: 3, label: 'Kick risk (60+ days offline)', tone: 'danger' },
  { n: 4, label: 'Discord not linked', tone: 'info' },
  { n: 2, label: 'Level dropped in 90 days', tone: 'warn' },
]

const FEATURES = [
  { icon: CheckCircleIcon, title: 'Know who needs a nudge', desc: 'A single list of members at risk of being kicked, gone quiet, or missing a Discord link, each one a click from the filtered roster.' },
  { icon: BotIcon, title: 'See when the guild is awake', desc: 'An hourly activity graph of members online, plus live guild chat and the connection status of each bot.' },
  { icon: UsersIcon, title: 'Roster, ranks and levels', desc: 'Skyblock levels, 90-day progress, last login and message counts for every member, searchable and sortable.' },
  { icon: TrophyIcon, title: 'Leaderboards and dyes', desc: 'Message leaderboards by week, month and all time, and a collection view of every dye a player has unlocked.' },
]

export default function Landing() {
  return (
    <div className="landing">
      <header className="landing-bar">
        <span className="brand" style={{ padding: 0 }}>Bumble</span>
        <div className="head-actions">
          <ThemeToggle />
          <a href="/auth/discord" className="btn btn-primary">Sign in</a>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-copy">
          <span className="eyebrow reveal">Bumble Kindergarten and University</span>
          <h1 className="landing-title reveal" style={{ '--i': 1 } as React.CSSProperties}>
            Run the guild <em>calmly.</em>
          </h1>
          <p className="landing-sub reveal" style={{ '--i': 2 } as React.CSSProperties}>
            One quiet place to see who is online, who needs attention, and how both guilds are doing. Built for the officers who keep them running.
          </p>
          <div className="landing-cta reveal" style={{ '--i': 3 } as React.CSSProperties}>
            <a href="/auth/discord" className="btn btn-discord">
              <svg width="20" height="20" viewBox="0 0 127.14 96.36" fill="currentColor" aria-hidden="true">
                <path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1A105.25,105.25,0,0,0,126.6,80.22h0C129.24,52.84,122.09,29.11,107.7,8.07ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,46,53.89,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,46,96.12,53,91.08,65.69,84.69,65.69Z" />
              </svg>
              Continue with Discord
            </a>
            <GuestButton />
          </div>
          <p className="card-sub reveal" style={{ marginTop: 12, '--i': 4 } as React.CSSProperties}>Officers sign in with Discord. Guests can look around but cannot change anything.</p>
          {import.meta.env.DEV && (
            <button className="btn btn-ghost btn-sm" style={{ marginTop: 14 }} onClick={() => { localStorage.setItem('dev_bypass', '1'); window.location.href = '/' }}>
              Skip login (dev only)
            </button>
          )}
        </div>

        <div className="landing-preview" aria-hidden="true">
          <div className="card preview-main reveal" style={{ '--i': 3 } as React.CSSProperties}>
            <div className="preview-head">
              <span className="card-title">Bumble Kindergarten</span>
              <span className="badge badge-on"><span className="dot on" />Connected</span>
            </div>
            <div className="preview-kpis">
              {[['126', 'Members'], ['38', 'Online now'], ['214', 'Average level']].map(([v, l]) => (
                <div key={l}><div className="k-value num" style={{ fontSize: 26 }}>{v}</div><div className="k-sub">{l}</div></div>
              ))}
            </div>
            <ActivityChart points={samplePoints()} />
          </div>
          <div className="card preview-attn reveal" style={{ '--i': 5 } as React.CSSProperties}>
            <div className="card-head" style={{ padding: '14px 18px 4px' }}><span className="card-title">Needs attention</span></div>
            {PREVIEW_ATTENTION.map(a => (
              <div key={a.label} className={`attn ${a.tone}`} style={{ padding: '9px 18px' }}>
                <span className="attn-count num">{a.n}</span>
                <span className="attn-body"><div className="attn-label" style={{ fontSize: 13 }}>{a.label}</div></span>
                <ArrowRightIcon className="attn-go" width={14} height={14} />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-features">
        {FEATURES.map((f, i) => (
          <div key={f.title} className="reveal" style={{ '--i': 6 + i } as React.CSSProperties}>
            <div className="feature-icon"><f.icon width={20} height={20} /></div>
            <h3>{f.title}</h3>
            <p>{f.desc}</p>
          </div>
        ))}
      </section>

      <footer className="landing-foot">
        <span>Bumble Bridge Bot for Hypixel Skyblock guilds</span>
        <a href="/auth/discord" style={{ fontWeight: 700 }}>Sign in</a>
      </footer>
    </div>
  )
}
