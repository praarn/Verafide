import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Sidebar from './Sidebar'

export default function ProtectedLayout({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--color-ink)] font-mono text-sm text-[var(--color-slate)]">
        Loading session…
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex h-screen bg-[var(--color-ink)] text-[var(--color-paper)]">
      <Sidebar />
      <main className="flex-1 overflow-y-auto scrollbar-thin">{children}</main>
    </div>
  )
}
