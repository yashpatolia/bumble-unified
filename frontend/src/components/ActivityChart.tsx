import { useMemo } from 'react'
import type { ActivityPoint } from '../types'
import { AreaChart, type Slot } from './AreaChart'

const HOURS = 24

/** Members online by hour for the last 24h. */
export function ActivityChart({ points }: { points: ActivityPoint[] }) {
  const slots: Slot[] = useMemo(() => {
    const end = new Date()
    end.setMinutes(0, 0, 0)
    const byHour = new Map(points.map(p => {
      const d = new Date(p.t)
      d.setMinutes(0, 0, 0)
      return [d.getTime(), p.online] as const
    }))
    return Array.from({ length: HOURS }, (_, i) => {
      const time = new Date(end.getTime() - (HOURS - 1 - i) * 3600000)
      return { label: `${String(time.getHours()).padStart(2, '0')}:00`, value: byHour.get(time.getTime()) ?? null }
    })
  }, [points])

  if (slots.every(s => s.value == null)) {
    return (
      <div className="chart-empty">
        No activity recorded yet. The bot samples who is online every 10 minutes, so the graph fills in shortly after it connects.
      </div>
    )
  }
  return <AreaChart slots={slots} xTicks={[0, 6, 12, 18, 23]} yMode="zero" unit="online" ariaLabel="Members online by hour" />
}
