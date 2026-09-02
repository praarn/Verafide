type Accent = "signal" | "verified" | "flagged" | "slate";

const ACCENT: Record<Accent, string> = {
  signal: "var(--color-signal)",
  verified: "var(--color-verified)",
  flagged: "var(--color-flagged)",
  slate: "var(--color-slate)",
};

export default function StatCard({
  label,
  value,
  sub,
  accent = "signal",
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: Accent;
}) {
  return (
    <div className="card p-5">
      <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">{label}</p>
      <p className="mt-2 font-display text-3xl font-semibold" style={{ color: ACCENT[accent] }}>
        {value}
      </p>
      {sub && <p className="mt-1 text-sm text-[var(--color-slate)]">{sub}</p>}
    </div>
  );
}
