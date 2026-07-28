import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Stamp } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setBusy(true)
    try {
      await register(email, password, fullName)
      navigate('/app')
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create your account.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--color-ink)] px-6 text-[var(--color-paper)]">
      <div className="w-full max-w-sm">
        <Link to="/" className="mb-8 flex items-center justify-center gap-2">
          <Stamp size={22} className="text-[var(--color-signal)]" />
          <span className="font-display text-xl font-semibold">Verafide</span>
        </Link>
        <div className="bg-grain rounded-xl border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-8">
          <h1 className="font-display text-2xl font-semibold">Open a case</h1>
          <p className="mt-1 text-sm text-[var(--color-slate)]">Create your desk account — free, no credit card.</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-md border border-[var(--color-line)] bg-[var(--color-ink)] px-3 py-2.5 text-sm outline-none focus:border-[var(--color-signal)]"
                placeholder="Jamie Reyes"
              />
            </div>
            <div>
              <label className="mb-1.5 block font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-[var(--color-line)] bg-[var(--color-ink)] px-3 py-2.5 text-sm outline-none focus:border-[var(--color-signal)]"
                placeholder="you@newsroom.com"
              />
            </div>
            <div>
              <label className="mb-1.5 block font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-[var(--color-line)] bg-[var(--color-ink)] px-3 py-2.5 text-sm outline-none focus:border-[var(--color-signal)]"
                placeholder="At least 8 characters"
              />
            </div>
            {error && <p className="text-sm text-[var(--color-flagged)]">{error}</p>}
            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-md bg-[var(--color-signal)] py-2.5 text-sm font-semibold text-[var(--color-ink)] transition-transform hover:scale-[1.01] disabled:opacity-60"
            >
              {busy ? 'Creating account…' : 'Create account'}
            </button>
          </form>
        </div>
        <p className="mt-6 text-center text-sm text-[var(--color-slate)]">
          Already have a desk?{' '}
          <Link to="/login" className="font-medium text-[var(--color-signal)]">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
