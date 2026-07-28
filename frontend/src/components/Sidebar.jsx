import { NavLink, useNavigate } from 'react-router-dom'
import { ScanSearch, History, Upload, BarChart3, LogOut, Stamp } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/app', label: 'Analyze', icon: ScanSearch, end: true },
  { to: '/app/history', label: 'Case History', icon: History },
  { to: '/app/batch', label: 'Batch Review', icon: Upload },
  { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-[var(--color-line)] bg-[var(--color-ink-soft)]">
      <div className="flex items-center gap-2 px-6 py-6">
        <Stamp size={22} className="text-[var(--color-signal)]" />
        <span className="font-display text-xl font-semibold tracking-tight">Verafide</span>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {links.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-[var(--color-signal)]/15 text-[var(--color-signal)]'
                  : 'text-[var(--color-slate)] hover:bg-white/5 hover:text-[var(--color-paper)]'
              }`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="rule mx-3 px-3 py-4">
        <p className="truncate text-sm font-medium">{user?.full_name || user?.email}</p>
        <p className="truncate font-mono text-xs text-[var(--color-slate)]">{user?.email}</p>
        <button
          onClick={handleLogout}
          className="mt-3 flex items-center gap-2 text-xs font-medium text-[var(--color-slate)] transition-colors hover:text-[var(--color-flagged)]"
        >
          <LogOut size={14} /> Sign out
        </button>
      </div>
    </aside>
  )
}
