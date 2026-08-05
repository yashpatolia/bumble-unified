import { useEffect } from 'react'

/**
 * Run `callback` immediately, then again every `intervalMs`, until the
 * component unmounts or a value in `deps` changes (which restarts the
 * interval, same as a normal useEffect dependency array).
 */
export function usePolling(callback: () => void, intervalMs: number, deps: unknown[] = []) {
  useEffect(() => {
    callback()
    const id = setInterval(callback, intervalMs)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
