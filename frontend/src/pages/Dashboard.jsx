import { useState } from 'react'
import { Link2, FileText, Sparkles } from 'lucide-react'
import api from '../api/client'
import VerdictStamp from '../components/VerdictStamp'
import AssistPanel from '../components/AssistPanel'
import Loader from '../components/Loader'

const SAMPLE_TEXTS = {
  fake: "You won't believe what secret documents reveal: officials are quietly hiding a miracle cure because it threatens billions in profits. Share before this gets DELETED!!!",
  real: 'In a statement, the Department of Health confirmed a modest decline in flu cases this season, according to figures released Tuesday. Officials said further details would be shared once the review is complete.',
}

export default function Dashboard() {
  const [inputType, setInputType] = useState('text')
  const [text, setText] = useState('')
  const [url, setUrl] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const handleAnalyze = async (e) => {
    e.preventDefault()
    setError('')
    setResult(null)
    setBusy(true)
    try {
      if (inputType === 'text') {
        const res = await api.post('/predict/text', { text, mode: 'classic' })
        setResult(res.data)
      } else {
        const res = await api.post('/predict/url', { url, mode: 'classic' })
        setResult(res.data)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong analyzing that input.')
    } finally {
      setBusy(false)
    }
  }

  const loadSample = (kind) => {
    setInputType('text')
    setText(SAMPLE_TEXTS[kind])
    setResult(null)
    setError('')
  }

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-signal)]">Case intake</p>
      <h1 className="mt-1 font-display text-3xl font-semibold">Analyze a story</h1>
      <p className="mt-2 max-w-xl text-sm text-[var(--color-slate)]">
        Paste article text or a link. Verafide scores the language and hands back a verdict with the words that mattered most.
      </p>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <form onSubmit={handleAnalyze} className="rounded-xl border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-6">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setInputType('text')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                inputType === 'text' ? 'bg-[var(--color-signal)] text-[var(--color-ink)]' : 'text-[var(--color-slate)] hover:bg-white/5'
              }`}
            >
              <FileText size={14} /> Text
            </button>
            <button
              type="button"
              onClick={() => setInputType('url')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                inputType === 'url' ? 'bg-[var(--color-signal)] text-[var(--color-ink)]' : 'text-[var(--color-slate)] hover:bg-white/5'
              }`}
            >
              <Link2 size={14} /> URL
            </button>
          </div>

          <div className="mt-4">
            {inputType === 'text' ? (
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                required
                minLength={20}
                rows={9}
                placeholder="Paste the headline or article body here…"
                className="w-full resize-none rounded-md border border-[var(--color-line)] bg-[var(--color-ink)] p-3 text-sm leading-relaxed outline-none focus:border-[var(--color-signal)]"
              />
            ) : (
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                placeholder="https://example-news-site.com/article"
                className="w-full rounded-md border border-[var(--color-line)] bg-[var(--color-ink)] p-3 text-sm outline-none focus:border-[var(--color-signal)]"
              />
            )}
          </div>

          <div className="mt-3 flex items-center gap-3">
            <button
              type="button"
              onClick={() => loadSample('fake')}
              className="font-mono text-[11px] text-[var(--color-slate)] underline decoration-dotted hover:text-[var(--color-paper)]"
            >
              try a flagged sample
            </button>
            <button
              type="button"
              onClick={() => loadSample('real')}
              className="font-mono text-[11px] text-[var(--color-slate)] underline decoration-dotted hover:text-[var(--color-paper)]"
            >
              try a verified sample
            </button>
          </div>

          {error && <p className="mt-3 text-sm text-[var(--color-flagged)]">{error}</p>}

          <button
            type="submit"
            disabled={busy}
            className="mt-5 flex items-center gap-2 rounded-md bg-[var(--color-signal)] px-5 py-2.5 text-sm font-semibold text-[var(--color-ink)] transition-transform hover:scale-[1.02] disabled:opacity-60"
          >
            <Sparkles size={16} />
            {busy ? 'Analyzing…' : 'Run analysis'}
          </button>
        </form>

        <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-6">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Verdict</p>
          {busy && (
            <div className="mt-10 flex justify-center">
              <Loader label="Reading the story" />
            </div>
          )}
          {!busy && !result && (
            <p className="mt-10 text-center text-sm text-[var(--color-slate)]">Run an analysis to see the stamp land here.</p>
          )}
          {!busy && result && (
            <div className="mt-4">
              <div className="flex items-center justify-center py-4">
                <VerdictStamp label={result.label} confidence={result.confidence} />
              </div>
              {result.source_title && (
                <p className="mb-3 truncate text-center text-sm font-medium">{result.source_title}</p>
              )}
              <div className="flex justify-center">
                <span className="mb-2 rounded-full bg-black/20 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-[var(--color-slate)]">
                  {result.verdict_source === 'llm' ? 'AI-reasoned verdict' : 'Pattern-based verdict'}
                </span>
              </div>
              {result.llm_reasoning && (
                <p className="mb-3 text-center text-sm italic text-[var(--color-slate)]">{result.llm_reasoning}</p>
              )}
              <div className="rule pt-4">
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
              {result.signal_words?.length > 0 && (
                <div className="rule mt-4 pt-4">
                  <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Signal words</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {result.signal_words.map((w) => (
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
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {!busy && result && <AssistPanel text={result.analyzed_text} />}
    </div>
  )
}
