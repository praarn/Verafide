"use client";

import { AlertTriangle, Download, FileSpreadsheet, ScanText } from "lucide-react";
import { Fragment, useState } from "react";

import AssistPanel from "@/components/AssistPanel";
import FileDrop from "@/components/FileDrop";
import PageHeader from "@/components/PageHeader";
import { errorMessage } from "@/lib/api";
import { runBatchJob, type BatchProgress } from "@/lib/batchJob";
import { downloadCsv } from "@/lib/exportCsv";
import type { BatchResponse } from "@/lib/types";
import { verdictWord } from "@/lib/verdict";

export default function BatchPage() {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<BatchProgress | null>(null);
  const [result, setResult] = useState<BatchResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    setResult(null);
    setProgress({ state: "pending", processed: 0, total: 0 });
    try {
      const final = await runBatchJob(file, setProgress);
      if (final.state === "error") setError(final.error || "The batch job failed.");
      else setResult(final.result);
    } catch (err) {
      setError(errorMessage(err, "Could not process that file."));
    } finally {
      setBusy(false);
    }
  };

  const exportCsv = () => {
    if (!result?.results.length) return;
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    downloadCsv(
      ["source_ref", "verdict", "confidence_pct", "confidence_band", "signal_words", "excerpt"],
      result.results.map((r) => [
        r.source_ref || "",
        r.label,
        Math.round(r.confidence * 100),
        r.confidence_band,
        r.signal_words.map((w) => w.word).join(" "),
        r.text_excerpt,
      ]),
      `verafide-batch-${stamp}.csv`,
    );
  };

  const pct = progress && progress.total ? Math.round((progress.processed / progress.total) * 100) : 0;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10 md:px-8">
      <PageHeader eyebrow="Batch review" title="Run a whole desk of stories">
        Upload a CSV with a <code className="font-mono text-[var(--color-signal)]">text</code> column, or a PDF
        (each page is analyzed as its own story). Progress streams live over a WebSocket. Up to 200 rows/pages.
      </PageHeader>

      <form onSubmit={submit} className="card p-6">
        <FileDrop
          accept=".csv,.pdf"
          file={file}
          onFile={setFile}
          hint="Drop a .csv or .pdf file, or click to choose"
        />
        <div className="mt-4 flex items-center justify-end">
          <button
            type="submit"
            disabled={!file || busy}
            className="rounded-md bg-[var(--color-signal)] px-5 py-2.5 text-sm font-semibold text-[var(--color-ink)] transition-transform hover:scale-[1.02] disabled:opacity-50"
          >
            {busy ? "Processing…" : "Analyze file"}
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-[var(--color-flagged)]">{error}</p>}
      </form>

      {busy && progress && (
        <div className="card mt-8 p-5">
          <div className="flex items-center justify-between font-mono text-[11px] uppercase tracking-widest text-[var(--color-slate)]">
            <span>{progress.state === "pending" ? "Reading file…" : `Classifying ${progress.processed}/${progress.total}`}</span>
            <span>{pct}%</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-black/30">
            <div className="h-full bg-[var(--color-signal)] transition-[width] duration-300" style={{ width: `${pct}%` }} />
          </div>
          <p className="mt-2 font-mono text-[11px] text-[var(--color-slate)]">
            Scanned / broken-encoding pages need OCR and take longer.
          </p>
        </div>
      )}

      {result && (
        <div className="mt-8">
          {result.extraction_summary && <ExtractionSummary summary={result.extraction_summary} />}

          {result.results.length > 0 && (
            <div className="mb-3 flex justify-end">
              <button
                type="button"
                onClick={exportCsv}
                className="flex items-center gap-1.5 rounded-md border border-[var(--color-line)] px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-[var(--color-slate)] transition-colors hover:border-[var(--color-signal)] hover:text-[var(--color-paper)]"
              >
                <Download size={13} /> Export CSV
              </button>
            </div>
          )}

          <div className="grid grid-cols-3 gap-4">
            <Stat label="Items analyzed" value={result.total} />
            <Stat label="Flagged" value={result.fake_count} color="var(--color-flagged)" />
            <Stat label="Verified" value={result.real_count} color="var(--color-verified)" />
          </div>

          <div className="mt-4 max-h-[420px] overflow-y-auto rounded-xl border border-[var(--color-line)] scrollbar-thin">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Batch classification results</caption>
              <thead className="sticky top-0 bg-[var(--color-ink-soft)] font-mono text-[11px] uppercase tracking-widest text-[var(--color-slate)]">
                <tr>
                  <th className="px-4 py-3">Excerpt</th>
                  <th className="px-4 py-3">Verdict</th>
                  <th className="px-4 py-3">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((row, i) => (
                  <Fragment key={i}>
                    <tr
                      onClick={() => setExpanded(expanded === i ? null : i)}
                      className="cursor-pointer border-t border-[var(--color-line)] hover:bg-white/5"
                    >
                      <td className="max-w-md truncate px-4 py-3 text-[var(--color-slate)]">
                        {row.source_ref && (
                          <span className="mr-2 font-mono text-[10px] uppercase text-[var(--color-signal)]">{row.source_ref}</span>
                        )}
                        {row.text_excerpt}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className="rounded-full px-2.5 py-1 font-mono text-[11px] font-semibold"
                          style={{
                            backgroundColor: row.label === "real" ? "var(--color-verified-soft)" : "var(--color-flagged-soft)",
                            color: row.label === "real" ? "var(--color-verified)" : "var(--color-flagged)",
                          }}
                        >
                          {verdictWord(row.label, row.confidence_band)}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono">
                        {Math.round(row.confidence * 100)}%
                        {row.confidence_band === "low" && (
                          <span className="ml-1.5 text-[10px] uppercase text-[var(--color-slate)]">low</span>
                        )}
                      </td>
                    </tr>
                    {expanded === i && (
                      <tr className="border-t border-[var(--color-line)] bg-black/20">
                        <td colSpan={3} className="px-4 py-4">
                          <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-[var(--color-slate)]">Full excerpt</p>
                          <p className="mb-3 text-sm text-[var(--color-paper)]">{row.text_excerpt}</p>
                          {row.signal_words.length > 0 ? (
                            <div className="flex flex-wrap gap-1.5">
                              {row.signal_words.map((w) => (
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
                          ) : (
                            <p className="text-sm text-[var(--color-slate)]">No strong signal words detected.</p>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 font-mono text-[11px] text-[var(--color-slate)]">Click a row for the full text and signal words.</p>

          {result.combined_text && <AssistPanel text={result.combined_text} label="whole document" />}
        </div>
      )}

      {!result && !busy && (
        <div className="mt-8 flex items-center gap-2 font-mono text-xs text-[var(--color-slate)]">
          <FileSpreadsheet size={14} /> Results appear here as a table once the file finishes processing.
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="rounded-lg border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-4 text-center">
      <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">{label}</p>
      <p className="mt-1 font-display text-2xl font-semibold" style={{ color }}>
        {value}
      </p>
    </div>
  );
}

function ExtractionSummary({ summary }: { summary: Record<string, unknown> }) {
  const num = (k: string) => (typeof summary[k] === "number" ? (summary[k] as number) : undefined);
  const totalPages = num("total_pages");
  const textPages = num("text_pages");
  const ocrPages = num("ocr_pages") ?? 0;
  const failedPages = num("failed_pages") ?? 0;
  const ocrAvailable = summary["ocr_available"] as boolean | undefined;
  const skipped = num("chunks_skipped_at_classification") ?? 0;
  if (totalPages == null && num("chunks_extracted") == null) return null;

  return (
    <div className="mb-4 rounded-lg border border-[var(--color-line)] bg-black/20 p-4">
      <div className="flex items-center gap-2">
        <ScanText size={15} className="text-[var(--color-signal)]" />
        <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">PDF extraction report</p>
      </div>
      {totalPages != null && (
        <p className="mt-2 text-sm text-[var(--color-paper)]">
          {totalPages} page{totalPages === 1 ? "" : "s"} —{" "}
          <span className="text-[var(--color-verified)]">{textPages} with normal text</span>
          {ocrPages > 0 && <>, <span className="text-[var(--color-signal)]">{ocrPages} recovered via OCR</span></>}
          {failedPages > 0 && <>, <span className="text-[var(--color-flagged)]">{failedPages} unreadable</span></>}.
        </p>
      )}
      {skipped > 0 && (
        <p className="mt-1 text-sm text-[var(--color-slate)]">
          {skipped} chunk{skipped === 1 ? "" : "s"} skipped during analysis (little readable English content).
        </p>
      )}
      {failedPages > 0 && !ocrAvailable && (
        <div className="mt-2 flex items-start gap-2 text-sm text-[var(--color-flagged)]">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span>OCR isn&rsquo;t available on this server, so scanned pages couldn&rsquo;t be read.</span>
        </div>
      )}
    </div>
  );
}
