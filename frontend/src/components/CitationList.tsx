import { BookOpen } from "lucide-react";

import type { Citation } from "@/lib/types";

export default function CitationList({
  citations,
  title = "Grounded in",
}: {
  citations: Citation[];
  title?: string;
}) {
  if (!citations?.length) return null;
  return (
    <div className="rule mt-4 pt-4">
      <div className="flex items-center gap-1.5">
        <BookOpen size={13} className="text-[var(--color-signal)]" aria-hidden="true" />
        <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">{title}</p>
      </div>
      <ul className="mt-2 space-y-2">
        {citations.map((c) => (
          <li key={c.id} className="rounded-md border border-[var(--color-line)] bg-black/20 p-3">
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-sm font-medium text-[var(--color-paper)]">{c.title}</p>
              <span className="shrink-0 font-mono text-[10px] text-[var(--color-slate)]">
                {(c.score * 100).toFixed(0)}% match
              </span>
            </div>
            <p className="mt-1 line-clamp-3 text-sm text-[var(--color-slate)]">{c.snippet}</p>
            <p className="mt-1 font-mono text-[10px] uppercase tracking-wide text-[var(--color-slate)]">
              {c.source}
            </p>
          </li>
        ))}
      </ul>
      <p className="mt-2 font-mono text-[10px] text-[var(--color-slate)]">
        Retrieved from Verafide&rsquo;s media-literacy corpus &amp; fact-check index — reference context, not proof.
      </p>
    </div>
  );
}
