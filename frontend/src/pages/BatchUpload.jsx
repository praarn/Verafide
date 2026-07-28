import { useState, useRef } from 'react'
import { UploadCloud, FileSpreadsheet, ScanText, AlertTriangle } from 'lucide-react'
import api from '../api/client'
import Loader from '../components/Loader'
import AssistPanel from '../components/AssistPanel'

export default function BatchUpload() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [expandedRow, setExpandedRow] = useState(null)
  const inputRef = useRef(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError('')
    setResult(null)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await api.post('/predict/batch', formData, {
        params: { mode: 'classic' },
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not process that file.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-signal)]">Batch review</p>
      <h1 className="mt-1 font-display text-3xl font-semibold">Run a whole desk of stories</h1>
      <p className="mt-2 max-w-xl text-sm text-[var(--color-slate)]">
        Upload a CSV with a <code className="font-mono text-[var(--color-signal)]">text</code> column (or
        <code className="font-mono text-[var(--color-signal)]"> article</code> /
        <code className="font-mono text-[var(--color-signal)]"> content</code> /
        <code className="font-mono text-[var(--color-signal)]"> headline</code>), or a PDF (each page is analyzed
        as its own story). Up to 200 rows/pages per file.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 rounded-xl border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-6">
        <div
          onClick={() => inputRef.current?.click()}
          className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-[var(--color-line)] py-10 text-center transition-colors hover:border-[var(--color-signal)]"
        >
          <UploadCloud size={28} className="text-[var(--color-slate)]" />
          <p className="text-sm">{file ? file.name : 'Click to choose a .csv or .pdf file'}</p>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.pdf"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </div>

        <div className="mt-4 flex items-center justify-end">
          <button
            type="submit"
            disabled={!file || busy}
            className="rounded-md bg-[var(--color-signal)] px-5 py-2.5 text-sm font-semibold text-[var(--color-ink)] transition-transform hover:scale-[1.02] disabled:opacity-60"
          >
            {busy ? 'Processing…' : 'Analyze file'}
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-[var(--color-flagged)]">{error}</p>}
      </form>

      {busy && (
        <div className="mt-8">
          <Loader label="Working through the batch" />
          <p className="mt-2 font-mono text-[11px] text-[var(--color-slate)]">
            Scanned or broken-encoding pages need OCR and can take longer — large PDFs may take up to a minute or so.
          </p>
        </div>
      )}

      {result && (
        <div className="mt-8">
          {result.extraction_summary && (
            <ExtractionSummaryBanner summary={result.extraction_summary} />
          )}
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-4 text-center">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Items analyzed</p>
              <p className="mt-1 font-display text-2xl font-semibold">{result.total}</p>
            </div>
            <div className="rounded-lg border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-4 text-center">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-flagged)]">Flagged</p>
              <p className="mt-1 font-display text-2xl font-semibold text-[var(--color-flagged)]">{result.fake_count}</p>
            </div>
            <div className="rounded-lg border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-4 text-center">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-verified)]">Verified</p>
              <p className="mt-1 font-display text-2xl font-semibold text-[var(--color-verified)]">{result.real_count}</p>
            </div>
          </div>

          <div className="mt-4 max-h-[420px] overflow-y-auto rounded-xl border border-[var(--color-line)] scrollbar-thin">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-[var(--color-ink-soft)] font-mono text-[11px] uppercase tracking-widest text-[var(--color-slate)]">
                <tr>
                  <th className="px-4 py-3">Excerpt</th>
                  <th className="px-4 py-3">Verdict</th>
                  <th className="px-4 py-3">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((row, i) => (
                  <>
                    <tr
                      key={i}
                      onClick={() => setExpandedRow(expandedRow === i ? null : i)}
                      className="cursor-pointer border-t border-[var(--color-line)] hover:bg-white/5"
                    >
                      <td className="max-w-md truncate px-4 py-3 text-[var(--color-slate)]">
                        {row.source_ref && (
                          <span className="mr-2 font-mono text-[10px] uppercase text-[var(--color-signal)]">
                            {row.source_ref}
                          </span>
                        )}
                        {row.text_excerpt}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className="rounded-full px-2.5 py-1 font-mono text-[11px] font-semibold"
                          style={{
                            backgroundColor: row.label === 'real' ? 'var(--color-verified-soft)' : 'var(--color-flagged-soft)',
                            color: row.label === 'real' ? 'var(--color-verified)' : 'var(--color-flagged)',
                          }}
                        >
                          {row.label === 'real' ? 'VERIFIED' : 'FLAGGED'}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono">{Math.round(row.confidence * 100)}%</td>
                    </tr>
                    {expandedRow === i && (
                      <tr className="border-t border-[var(--color-line)] bg-black/20">
                        <td colSpan={3} className="px-4 py-4">
                          <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-[var(--color-slate)]">
                            Full excerpt
                          </p>
                          <p className="mb-3 text-sm text-[var(--color-paper)]">{row.text_excerpt}</p>
                          {row.signal_words?.length > 0 ? (
                            <>
                              <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-[var(--color-slate)]">
                                Signal words
                              </p>
                              <div className="flex flex-wrap gap-1.5">
                                {row.signal_words.map((w) => (
                                  <span
                                    key={w.word}
                                    className="rounded-full px-2.5 py-1 font-mono text-[11px]"
                                    style={{
                                      backgroundColor: w.direction === 'real' ? 'var(--color-verified-soft)' : 'var(--color-flagged-soft)',
                                      color: w.direction === 'real' ? 'var(--color-verified)' : 'var(--color-flagged)',
                                    }}
                                  >
                                    {w.word}
                                  </span>
                                ))}
                              </div>
                            </>
                          ) : (
                            <p className="text-sm text-[var(--color-slate)]">No strong signal words detected.</p>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 font-mono text-[11px] text-[var(--color-slate)]">Click a row to see the full text and signal words.</p>

          {result.combined_text && <AssistPanel text={result.combined_text} label="whole document" />}
        </div>
      )}

      {!result && !busy && (
        <div className="mt-8 flex items-center gap-2 font-mono text-xs text-[var(--color-slate)]">
          <FileSpreadsheet size={14} /> Results will appear here as a table once the file finishes processing.
        </div>
      )}
    </div>
  )
}

function ExtractionSummaryBanner({ summary }) {
  const { total_pages, text_pages, ocr_pages, failed_pages, ocr_available, chunks_extracted, chunks_skipped_at_classification, ocr_capped } = summary
  if (total_pages == null && chunks_extracted == null) return null

  const hadScannedPages = ocr_pages > 0 || failed_pages > 0
  const hadSkippedChunks = chunks_skipped_at_classification > 0

  return (
    <div className="mb-4 rounded-lg border border-[var(--color-line)] bg-black/20 p-4">
      <div className="flex items-center gap-2">
        <ScanText size={15} className="text-[var(--color-signal)]" />
        <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">PDF extraction report</p>
      </div>
      {total_pages != null && (
        <p className="mt-2 text-sm text-[var(--color-paper)]">
          {total_pages} page{total_pages === 1 ? '' : 's'} total —{' '}
          <span className="text-[var(--color-verified)]">{text_pages} with normal text</span>
          {ocr_pages > 0 && (
            <>
              , <span className="text-[var(--color-signal)]">{ocr_pages} recovered via OCR</span> (scanned/image pages)
            </>
          )}
          {failed_pages > 0 && (
            <>
              , <span className="text-[var(--color-flagged)]">{failed_pages} unreadable</span>
            </>
          )}
          .
        </p>
      )}
      {chunks_extracted != null && (
        <p className="mt-1 text-sm text-[var(--color-paper)]">
          {chunks_extracted} text chunk{chunks_extracted === 1 ? '' : 's'} extracted
          {hadSkippedChunks && (
            <>
              , but <span className="text-[var(--color-flagged)]">{chunks_skipped_at_classification} were skipped during analysis</span> (likely little to no readable English content after cleanup — e.g. tables, ads, or non-English text)
            </>
          )}
          .
        </p>
      )}
      {failed_pages > 0 && !ocr_available && (
        <div className="mt-2 flex items-start gap-2 text-sm text-[var(--color-flagged)]">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span>
            OCR isn't available on this server (Tesseract not installed), so scanned/image pages couldn't be read.
            See the README for setup instructions.
          </span>
        </div>
      )}
      {failed_pages > 0 && ocr_available && (
        <p className="mt-2 text-sm text-[var(--color-slate)]">
          Those pages had no readable text even after OCR — likely low scan quality, a blank page, or a full-page image/ad.
        </p>
      )}
      {ocr_capped && (
        <p className="mt-2 text-sm text-[var(--color-slate)]">
          This document needed OCR on more pages than we process per upload — only the first batch was OCR'd to keep
          things responsive. Try splitting very long scanned PDFs into smaller files.
        </p>
      )}
      {hadScannedPages && (
        <p className="mt-2 font-mono text-[11px] text-[var(--color-slate)]">
          This looks like a scanned document. OCR is slower and less accurate than native text — treat results from
          recovered pages with extra caution.
        </p>
      )}
    </div>
  )
}
