import type { Verdict } from "@/lib/types";

const PALETTE: Record<Verdict, string> = {
  real: "var(--color-verified)",
  fake: "var(--color-flagged)",
};

export default function VerdictStamp({
  label,
  confidence,
  size = 128,
  animate = true,
}: {
  label: Verdict;
  confidence: number;
  size?: number;
  animate?: boolean;
}) {
  const color = PALETTE[label] ?? PALETTE.fake;
  const pct = Math.round(confidence * 100);
  const word = label === "real" ? "VERIFIED" : "FLAGGED";

  return (
    <div
      className={animate ? "verdict-stamp" : undefined}
      style={{ width: size, height: size, transform: animate ? undefined : "rotate(-8deg)" }}
      role="img"
      aria-label={`${word}, ${pct}% confidence`}
    >
      <svg viewBox="0 0 140 140" width={size} height={size}>
        <defs>
          <filter id="stamp-rough">
            <feTurbulence type="fractalNoise" baseFrequency="0.02 0.09" numOctaves="2" seed="7" result="noise" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="4" />
          </filter>
        </defs>
        <g filter="url(#stamp-rough)">
          <circle cx="70" cy="70" r="62" fill="none" stroke={color} strokeWidth="5" />
          <circle cx="70" cy="70" r="50" fill="none" stroke={color} strokeWidth="2" />
          <text x="70" y="66" textAnchor="middle" fontFamily="var(--font-mono)" fontWeight="700" fontSize="17" letterSpacing="1" fill={color}>
            {word}
          </text>
          <text x="70" y="88" textAnchor="middle" fontFamily="var(--font-mono)" fontWeight="600" fontSize="13" fill={color}>
            {pct}% CONF.
          </text>
        </g>
      </svg>
    </div>
  );
}
