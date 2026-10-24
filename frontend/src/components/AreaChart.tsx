import { useEffect, useRef, useState } from 'react'

const HEIGHT = 230
const PAD = { top: 14, right: 14, bottom: 26, left: 40 }

export interface Slot {
  label: string
  value: number | null
}

/** Smooth area chart over evenly spaced slots. Null slots are gaps, not zeros, so a
 * missing hour or day never reads as a real drop. `yMode` 'zero' anchors the axis at 0
 * (counts); 'fit' zooms to the data range (levels, where the change is the story). */
export function AreaChart({ slots, xTicks, yMode, unit, decimals = 0, ariaLabel }: {
  slots: Slot[]
  xTicks: number[]
  yMode: 'zero' | 'fit'
  unit: string
  decimals?: number
  ariaLabel: string
}) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(640)
  const [hover, setHover] = useState<number | null>(null)

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(() => setWidth(Math.max(280, el.clientWidth)))
    ro.observe(el)
    setWidth(Math.max(280, el.clientWidth))
    return () => ro.disconnect()
  }, [])

  const known = slots.filter(s => s.value != null).map(s => s.value as number)
  const n = slots.length
  const maxV = Math.max(...known)
  const minV = Math.min(...known)

  let lo = 0
  let hi: number
  if (yMode === 'zero') {
    hi = Math.max(5, Math.ceil(maxV / 5) * 5)
  } else {
    const span = Math.max(maxV - minV, 1)
    lo = Math.floor(minV - span * 0.25)
    hi = Math.ceil(maxV + span * 0.25)
    if (hi - lo < 2) hi = lo + 2
  }

  const innerW = width - PAD.left - PAD.right
  const innerH = HEIGHT - PAD.top - PAD.bottom
  const x = (i: number) => PAD.left + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW)
  const y = (v: number) => PAD.top + innerH - ((v - lo) / (hi - lo)) * innerH
  const ticks = [lo, (lo + hi) / 2, hi]

  const runs: { i: number; v: number }[][] = []
  slots.forEach((s, i) => {
    if (s.value == null) { runs.push([]); return }
    if (runs.length === 0) runs.push([])
    runs[runs.length - 1].push({ i, v: s.value })
  })
  const validRuns = runs.filter(r => r.length > 0)
  const path = (run: { i: number; v: number }[]) => run.reduce((d, p, k) => {
    if (k === 0) return `M${x(p.i)},${y(p.v)}`
    const prev = run[k - 1]
    const mx = (x(prev.i) + x(p.i)) / 2
    return `${d} C${mx},${y(prev.v)} ${mx},${y(p.v)} ${x(p.i)},${y(p.v)}`
  }, '')

  const hovered = hover != null ? slots[hover] : null
  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const rel = (e.clientX - rect.left - PAD.left) / innerW
    setHover(Math.min(n - 1, Math.max(0, Math.round(rel * (n - 1)))))
  }
  const fmt = (v: number) => v.toFixed(decimals)

  return (
    <div className="chart-wrap" ref={wrapRef}>
      <svg width={width} height={HEIGHT} onMouseMove={onMove} onMouseLeave={() => setHover(null)} role="img" aria-label={ariaLabel}>
        {ticks.map((t, k) => (
          <g key={k}>
            <line className="chart-grid" x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} />
            <text className="chart-axis" x={PAD.left - 8} y={y(t) + 4} textAnchor="end">{decimals === 0 ? Math.round(t) : fmt(t)}</text>
          </g>
        ))}
        {xTicks.map((i, k) => (
          <text key={i} className="chart-axis" x={x(i)} y={HEIGHT - 6} textAnchor={k === 0 ? 'start' : k === xTicks.length - 1 ? 'end' : 'middle'}>
            {slots[i]?.label}
          </text>
        ))}
        {validRuns.map((run, k) => (
          <g key={k}>
            {run.length > 1 && (
              <path className="chart-area" d={`${path(run)} L${x(run[run.length - 1].i)},${y(lo)} L${x(run[0].i)},${y(lo)} Z`} />
            )}
            <path className="chart-line chart-draw" d={run.length > 1 ? path(run) : `M${x(run[0].i)},${y(run[0].v)} h0.01`} />
          </g>
        ))}
        {hovered && hovered.value != null && (
          <g>
            <line className="chart-cursor" x1={x(hover!)} x2={x(hover!)} y1={PAD.top} y2={PAD.top + innerH} />
            <circle className="chart-dot" cx={x(hover!)} cy={y(hovered.value)} r={5} />
          </g>
        )}
      </svg>
      {hovered && hovered.value != null && (
        <div className="chart-tip" style={{ left: x(hover!) + 12, top: y(hovered.value) + PAD.top }}>
          {hovered.label}: {fmt(hovered.value)}{unit ? ` ${unit}` : ''}
        </div>
      )}
    </div>
  )
}
