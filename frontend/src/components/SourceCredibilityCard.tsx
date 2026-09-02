import { Drama, Landmark, ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";

import type { SourceCredibility } from "@/lib/types";
import { TIER_COLOR } from "@/lib/verdict";

const ICON = {
  high: ShieldCheck,
  mixed: ShieldQuestion,
  low: ShieldAlert,
  satire: Drama,
  state: Landmark,
} as const;

export default function SourceCredibilityCard({ credibility }: { credibility: SourceCredibility | null }) {
  if (!credibility) return null;
  const Icon = ICON[credibility.tier] ?? ShieldQuestion;
  const color = TIER_COLOR[credibility.tier] ?? "var(--color-slate)";

  return (
    <div className="rule mt-4 pt-4">
      <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Source signal</p>
      <div className="mt-2 flex items-start gap-2.5">
        <Icon size={18} className="mt-0.5 shrink-0" style={{ color }} aria-hidden="true" />
        <div>
          <p className="text-sm font-semibold" style={{ color }}>
            {credibility.label}
            <span className="ml-1.5 font-mono text-[11px] font-normal text-[var(--color-slate)]">
              {credibility.domain}
            </span>
          </p>
          <p className="mt-0.5 text-sm text-[var(--color-slate)]">{credibility.blurb}</p>
        </div>
      </div>
      <p className="mt-2 font-mono text-[10px] text-[var(--color-slate)]">
        Publisher reputation only — it does not change the verdict, which is scored from the content.
      </p>
    </div>
  );
}
