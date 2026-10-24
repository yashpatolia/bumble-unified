import { useMemo } from 'react'
import type { LevelTrendPoint } from '../types'
import { AreaChart, type Slot } from './AreaChart'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function dayLabel(iso: string): string {
  const [, m, d] = iso.split('-').map(Number)
  return `${MONTHS[m - 1]} ${d}`
}

/** Guild average Skyblock level per day. */
export function LevelTrendChart({ points, days }: { points: LevelTrendPoint[]; days: number }) {
  const slots: Slot[] = useMemo(() => {
    const byDay = new Map(points.map(p => [p.t, p.avg]))
    const today = new Date()
    return Array.from({ length: days }, (_, i) => {
      const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (days - 1 - i))
      const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      return { label: dayLabel(iso), value: byDay.get(iso) ?? null }
    })
  }, [points, days])

  if (slots.filter(s => s.value != null).length < 2) {
    return <div className="chart-empty">Level history builds up one snapshot per member per day, so this graph needs a couple of days of data.</div>
  }
  const q = Math.floor((days - 1) / 4)
  return <AreaChart slots={slots} xTicks={[0, q, q * 2, q * 3, days - 1]} yMode="fit" unit="avg level" decimals={1} ariaLabel="Average Skyblock level over time" />
}
