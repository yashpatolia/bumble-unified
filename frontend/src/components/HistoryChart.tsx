import { useMemo } from 'react'
import { AreaChart, type Slot } from './AreaChart'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const isoDay = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

/** One value per day for a single member (level, Catacombs, slayer XP). The axis starts at the
 * first recorded day, so a newly tracked member gets a short, readable chart instead of 90 days
 * of mostly gaps. Days without a snapshot are gaps, not zeros. */
export function HistoryChart({ points, unit, decimals = 0, ariaLabel, height }: {
  points: { t: string; v: number | null }[]
  unit: string
  decimals?: number
  ariaLabel: string
  height?: number
}) {
  const slots: Slot[] = useMemo(() => {
    const known = points.filter(p => p.v != null)
    if (known.length === 0) return []
    const [y, m, d] = known[0].t.split('-').map(Number)
    const start = new Date(y, m - 1, d)
    const today = new Date()
    const days = Math.min(90, Math.max(2, Math.round((new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime() - start.getTime()) / 86400000) + 1))
    const byDay = new Map(known.map(p => [p.t, p.v as number]))
    return Array.from({ length: days }, (_, i) => {
      const day = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (days - 1 - i))
      return { label: `${MONTHS[day.getMonth()]} ${day.getDate()}`, value: byDay.get(isoDay(day)) ?? null }
    })
  }, [points])

  if (slots.filter(s => s.value != null).length < 2) {
    return <div className="chart-empty">History builds up one snapshot a day, so this chart needs a couple of days of data.</div>
  }
  const last = slots.length - 1
  const ticks = Array.from(new Set([0, 1, 2, 3, 4, 5, 6].map(i => Math.round((i / 6) * last))))
  return <AreaChart slots={slots} xTicks={ticks} yMode="fit" unit={unit} decimals={decimals} ariaLabel={ariaLabel} height={height} />
}
