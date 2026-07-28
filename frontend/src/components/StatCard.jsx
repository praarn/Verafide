export default function StatCard({ label, value, sub, accent = 'signal' }) {
  const accentColor = {
    signal: 'var(--color-signal)',
    verified: 'var(--color-verified)',
    flagged: 'var(--color-flagged)',
    slate: 'var(--color-slate)',
  }[accent]

  return (
    <div className="rounded-lg border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-5">
      <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">{label}</p>
      <p className="mt-2 font-display text-3xl font-semibold" style={{ color: accentColor }}>
        {value}
      </p>
      {sub && <p className="mt-1 text-sm text-[var(--color-slate)]">{sub}</p>}
    </div>
  )
}
