export default function PageHeader({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="mb-8">
      <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-signal)]">{eyebrow}</p>
      <h1 className="mt-1 font-display text-3xl font-semibold">{title}</h1>
      {children && <p className="mt-2 max-w-2xl text-sm text-[var(--color-slate)]">{children}</p>}
    </header>
  );
}
