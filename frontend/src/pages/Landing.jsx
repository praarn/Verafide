import { Link } from 'react-router-dom'
import { Stamp, ScanSearch, Link2, FileSpreadsheet, BarChart3, ArrowRight } from 'lucide-react'

const features = [
  {
    icon: ScanSearch,
    title: 'Paste & verify',
    body: 'Drop in a headline or full article and get a verdict with a confidence score in under a second.',
  },
  {
    icon: Link2,
    title: 'Check any URL',
    body: 'Hand it a link — Verafide pulls the article text itself and runs the same forensic pass.',
  },
  {
    icon: FileSpreadsheet,
    title: 'Batch the newsroom',
    body: 'Upload a CSV of articles and get every verdict back in one pass, ready to export.',
  },
  {
    icon: BarChart3,
    title: 'Track your desk',
    body: 'A running log of every case you\u2019ve checked, with trends across your review history.',
  },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-[var(--color-ink)] text-[var(--color-paper)]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <Stamp size={22} className="text-[var(--color-signal)]" />
          <span className="font-display text-xl font-semibold tracking-tight">Verafide</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="px-4 py-2 text-sm font-medium text-[var(--color-slate)] hover:text-[var(--color-paper)]">
            Sign in
          </Link>
          <Link
            to="/register"
            className="rounded-md bg-[var(--color-signal)] px-4 py-2 text-sm font-semibold text-[var(--color-ink)] transition-transform hover:scale-[1.03]"
          >
            Open a case
          </Link>
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl gap-12 px-6 pb-20 pt-12 md:grid-cols-2 md:items-center md:pt-20">
        <div>
          <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-[var(--color-signal)]">
            Verification desk &middot; est. for the credibility beat
          </p>
          <h1 className="font-display text-5xl font-semibold leading-[1.05] tracking-tight md:text-6xl">
            Run every headline
            <br />
            through the desk.
          </h1>
          <p className="mt-6 max-w-md text-lg text-[var(--color-slate)]">
            Verafide reads an article the way a skeptical editor would — scoring language patterns,
            sourcing cues, and rhetorical tells, then stamping a verdict you can act on.
          </p>
          <div className="mt-8 flex items-center gap-4">
            <Link
              to="/register"
              className="flex items-center gap-2 rounded-md bg-[var(--color-signal)] px-5 py-3 text-sm font-semibold text-[var(--color-ink)] transition-transform hover:scale-[1.03]"
            >
              Start analyzing <ArrowRight size={16} />
            </Link>
            <Link to="/login" className="text-sm font-medium text-[var(--color-slate)] hover:text-[var(--color-paper)]">
              I already have an account
            </Link>
          </div>
        </div>

        <div className="relative">
          <div className="bg-grain rounded-xl border border-[var(--color-line)] bg-[var(--color-paper)] p-6 text-[var(--color-ink)] shadow-2xl">
            <p className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-ink)]/50">Case #0417 &middot; Incoming text</p>
            <p className="mt-3 font-display text-lg leading-snug">
              &ldquo;You won&rsquo;t believe what secret documents reveal&hellip; share before this gets DELETED!!!&rdquo;
            </p>
            <div className="rule mt-4 border-[var(--color-ink)]/10 pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-flagged)]">Verdict</p>
                  <p className="font-display text-2xl font-semibold text-[var(--color-flagged)]">Flagged &middot; 98% confidence</p>
                </div>
                <div className="h-16 w-16 shrink-0 rounded-full border-2 border-[var(--color-flagged)]" style={{ transform: 'rotate(-8deg)' }}>
                  <div className="flex h-full w-full items-center justify-center font-mono text-[9px] font-bold text-[var(--color-flagged)]">
                    FLAGGED
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="absolute -bottom-4 -left-4 -z-10 h-full w-full rounded-xl border border-[var(--color-line)]" />
        </div>
      </section>

      <section className="border-y border-[var(--color-line)] bg-[var(--color-ink-soft)] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="font-display text-2xl font-semibold">What the desk handles</h2>
          <div className="mt-8 grid gap-6 md:grid-cols-4">
            {features.map(({ icon: Icon, title, body }) => (
              <div key={title} className="rounded-lg border border-[var(--color-line)] p-5">
                <Icon size={20} className="text-[var(--color-signal)]" />
                <p className="mt-3 font-display text-lg font-semibold">{title}</p>
                <p className="mt-2 text-sm leading-relaxed text-[var(--color-slate)]">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="mx-auto max-w-6xl px-6 py-10 text-center font-mono text-xs text-[var(--color-slate)]">
        Verafide is a demonstration project. Verdicts are model estimates, not fact-checks — always confirm with primary sources.
      </footer>
    </div>
  )
}
