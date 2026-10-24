import { useTheme } from '../theme'
import { MoonIcon, SunIcon } from './icons'

export function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const next = theme === 'light' ? 'dark' : 'light'
  return (
    <button className="icon-btn" onClick={toggle} title={`Switch to ${next} mode`} aria-label={`Switch to ${next} mode`}>
      {theme === 'light' ? <MoonIcon /> : <SunIcon />}
    </button>
  )
}
