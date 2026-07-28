const palettes = {
  real: {
    ring: 'var(--color-verified)',
    text: 'var(--color-verified)',
  },
  fake: {
    ring: 'var(--color-flagged)',
    text: 'var(--color-flagged)',
  },
}

export default function VerdictStamp({ label, confidence, size = 128, animate = true }) {
  const palette = palettes[label] ?? palettes.fake
  const pct = Math.round(confidence * 100)
  const word = label === 'real' ? 'VERIFIED' : 'FLAGGED'

  return (
    <div
      className={animate ? 'verdict-stamp' : ''}
      style={{ width: size, height: size, transform: animate ? undefined : 'rotate(-8deg)' }}
    >
      <svg viewBox="0 0 140 140" width={size} height={size}>
        <defs>
          <filter id="stamp-rough">
            <feTurbulence type="fractalNoise" baseFrequency="0.02 0.09" numOctaves="2" seed="7" result="noise" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="4" />
          </filter>
        </defs>
        <g filter="url(#stamp-rough)">
          <circle cx="70" cy="70" r="62" fill="none" stroke={palette.ring} strokeWidth="5" />
          <circle cx="70" cy="70" r="50" fill="none" stroke={palette.ring} strokeWidth="2" />
          <text
            x="70"
            y="66"
            textAnchor="middle"
            fontFamily="'IBM Plex Mono', monospace"
            fontWeight="700"
            fontSize="17"
            letterSpacing="1"
            fill={palette.text}
          >
            {word}
          </text>
          <text
            x="70"
            y="88"
            textAnchor="middle"
            fontFamily="'IBM Plex Mono', monospace"
            fontWeight="600"
            fontSize="13"
            fill={palette.text}
          >
            {pct}% CONF.
          </text>
        </g>
      </svg>
    </div>
  )
}
