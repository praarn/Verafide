import type { PredictResponse } from "@/lib/types";
import { bandMeta } from "@/lib/verdict";
import CitationList from "./CitationList";
import SourceCredibilityCard from "./SourceCredibilityCard";
import VerdictStamp from "./VerdictStamp";

export default function VerdictPanel({ result }: { result: PredictResponse }) {
  const band = bandMeta(result.confidence_band);

  return (
    <div className="mt-4">
      <div className="flex items-center justify-center py-4">
        <VerdictStamp label={result.label} confidence={result.confidence} />
      </div>

      {result.source_title && (
        <p className="mb-3 truncate text-center text-sm font-medium">{result.source_title}</p>
      )}

      <div className="flex flex-wrap justify-center gap-1.5">
        <Chip>{result.verdict_source === "llm" ? "AI-reasoned verdict" : "Pattern-based verdict"}</Chip>
        <Chip title={band.hint} color={band.color}>
          {band.label}
        </Chip>
        <Chip>{result.modality} input</Chip>
      </div>

      {result.llm_reasoning && (
        <p className="mt-3 text-center text-sm italic text-[var(--color-slate)]">{result.llm_reasoning}</p>
      )}

      <div className="rule mt-4 pt-4">
        <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Probability split</p>
        <div className="mt-2 flex h-2 overflow-hidden rounded-full bg-black/30">
          <div className="h-full bg-[var(--color-flagged)]" style={{ width: `${result.probabilities.fake * 100}%` }} />
          <div className="h-full bg-[var(--color-verified)]" style={{ width: `${result.probabilities.real * 100}%` }} />
        </div>
        <div className="mt-1 flex justify-between font-mono text-[11px] text-[var(--color-slate)]">
          <span>Fake {Math.round(result.probabilities.fake * 100)}%</span>
          <span>Real {Math.round(result.probabilities.real * 100)}%</span>
        </div>
      </div>

      <SourceCredibilityCard credibility={result.source_credibility} />
      <CitationList citations={result.citations} />

      {result.media_observations && (
        <div className="rule mt-4 pt-4">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Visual notes</p>
          <p className="mt-2 whitespace-pre-line text-sm text-[var(--color-slate)]">{result.media_observations}</p>
        </div>
      )}

      {(result.extracted_text || result.transcript) && (
        <details className="rule mt-4 pt-4">
          <summary className="cursor-pointer font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">
            {result.transcript ? "Transcript" : "Extracted text"}
          </summary>
          <p className="mt-2 whitespace-pre-line text-sm text-[var(--color-paper)]">
            {result.transcript || result.extracted_text}
          </p>
        </details>
      )}

      {result.signal_words.length > 0 && (
        <div className="rule mt-4 pt-4">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Signal words</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {result.signal_words.map((w) => (
              <span
                key={w.word}
                className="rounded-full px-2.5 py-1 font-mono text-[11px]"
                style={{
                  backgroundColor: w.direction === "real" ? "var(--color-verified-soft)" : "var(--color-flagged-soft)",
                  color: w.direction === "real" ? "var(--color-verified)" : "var(--color-flagged)",
                }}
              >
                {w.word}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Chip({ children, color, title }: { children: React.ReactNode; color?: string; title?: string }) {
  return (
    <span
      title={title}
      className="rounded-full bg-black/20 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-widest"
      style={{ color: color ?? "var(--color-slate)" }}
    >
      {children}
    </span>
  );
}
