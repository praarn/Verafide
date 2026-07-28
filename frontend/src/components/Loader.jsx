export default function Loader({ label = 'Working' }) {
  return (
    <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--color-signal)] opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--color-signal)]" />
      </span>
      {label}…
    </div>
  )
}
