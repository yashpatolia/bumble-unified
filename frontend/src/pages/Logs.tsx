import { useEffect, useRef, useState } from 'react'
import { wsLogsUrl } from '../api'
import type { LogRecord } from '../types'

const LEVEL_ORDER = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

export default function Logs() {
  const [records, setRecords] = useState<LogRecord[]>([])
  const [connected, setConnected] = useState(false)
  const [filter, setFilter] = useState<string>('INFO')
  const [search, setSearch] = useState('')
  const [pinned, setPinned] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let destroyed = false
    let retryTimer: ReturnType<typeof setTimeout>

    const connect = () => {
      const ws = new WebSocket(wsLogsUrl())
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!destroyed) retryTimer = setTimeout(connect, 3000)
      }
      ws.onerror = () => setConnected(false)
      ws.onmessage = (e) => {
        const record: LogRecord = JSON.parse(e.data)
        if (record.type === 'ping') return
        setRecords(prev => [...prev.slice(-2000), record])
      }
    }

    connect()
    return () => {
      destroyed = true
      clearTimeout(retryTimer)
      wsRef.current?.close()
    }
  }, [])

  useEffect(() => {
    if (pinned) bottomRef.current?.scrollIntoView()
  }, [records, pinned])

  const handleScroll = () => {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    setPinned(atBottom)
  }

  const minLevelIdx = LEVEL_ORDER.indexOf(filter)
  const visible = records.filter(r => {
    if (!r.level) return false
    if (LEVEL_ORDER.indexOf(r.level) < minLevelIdx) return false
    if (search && !r.message?.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  return (
    <div>
      <div className="log-toolbar">
        <div className="log-status">
          <span className={`status-dot ${connected ? 'online' : 'offline'}`} />
          {connected ? 'Connected' : 'Disconnected'}
        </div>
        <select
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="form-input"
          style={{ width: 110 }}
        >
          {LEVEL_ORDER.map(l => <option key={l}>{l}</option>)}
        </select>
        <input
          className="form-input"
          placeholder="Search messages..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ flex: 1, maxWidth: 300 }}
        />
        <button className="btn btn-ghost" onClick={() => setRecords([])}>Clear</button>
        <button
          className={`btn ${pinned ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => { setPinned(true); bottomRef.current?.scrollIntoView() }}
        >
          {pinned ? 'Pinned' : 'Pin to bottom'}
        </button>
      </div>
      <div className="log-container" ref={containerRef} onScroll={handleScroll}>
        {visible.length === 0 && <div className="empty">No log entries yet.</div>}
        {visible.map((r, i) => (
          <div className="log-line" key={i}>
            <span className="log-time">{r.time}</span>
            <span className={`log-level ${r.level}`}>{r.level}</span>
            <span className="log-source">{r.source}</span>
            <span className="log-msg">{r.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
