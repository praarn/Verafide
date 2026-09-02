import type { ConfidenceBand, CredibilityTier, Verdict } from "./types";

export const BAND_META: Record<ConfidenceBand, { label: string; hint: string; color: string }> = {
  high: {
    label: "High confidence",
    hint: "The model is strongly committed to this call.",
    color: "var(--color-verified)",
  },
  moderate: {
    label: "Moderate confidence",
    hint: "A reasonable call, but not clear-cut.",
    color: "var(--color-signal)",
  },
  low: {
    label: "Low confidence",
    hint: 'Close to a coin-flip — treat this as "leans", not a verdict.',
    color: "var(--color-flagged)",
  },
};

export function bandMeta(band: ConfidenceBand) {
  return BAND_META[band] ?? BAND_META.moderate;
}

export function verdictWord(label: Verdict | string, band?: ConfidenceBand): string {
  const real = label === "real";
  if (band === "low") return real ? "LEANS VERIFIED" : "LEANS FLAGGED";
  return real ? "VERIFIED" : "FLAGGED";
}

export const TIER_COLOR: Record<CredibilityTier, string> = {
  high: "var(--color-verified)",
  mixed: "var(--color-signal)",
  low: "var(--color-flagged)",
  satire: "var(--color-signal)",
  state: "var(--color-flagged)",
};
