"use client";

import { AudioLines, FileText, ImageIcon, Link2, Sparkles } from "lucide-react";
import { useState } from "react";

import AssistPanel from "@/components/AssistPanel";
import FileDrop from "@/components/FileDrop";
import Loader from "@/components/Loader";
import PageHeader from "@/components/PageHeader";
import VerdictPanel from "@/components/VerdictPanel";
import { api, errorMessage } from "@/lib/api";
import type { PredictResponse } from "@/lib/types";

type Tab = "text" | "url" | "image" | "audio";

const TABS: { id: Tab; label: string; icon: typeof FileText }[] = [
  { id: "text", label: "Text", icon: FileText },
  { id: "url", label: "URL", icon: Link2 },
  { id: "image", label: "Image", icon: ImageIcon },
  { id: "audio", label: "Audio", icon: AudioLines },
];

const SAMPLES = {
  fake: "You won't believe what secret documents reveal: officials are quietly hiding a miracle cure because it threatens billions in profits. Share before this gets DELETED!!!",
  real: "In a statement, the Department of Health confirmed a modest decline in flu cases this season, according to figures released Tuesday. Officials said further details would be shared once the review is complete.",
};

export default function AnalyzePage() {
  const [tab, setTab] = useState<Tab>("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const switchTab = (t: Tab) => {
    setTab(t);
    setResult(null);
    setError("");
    setFile(null);
  };

  const analyze = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setResult(null);
    setBusy(true);
    try {
      let res;
      if (tab === "text") {
        res = await api.post<PredictResponse>("/predict/text", { text, mode: "classic" });
      } else if (tab === "url") {
        res = await api.post<PredictResponse>("/predict/url", { url, mode: "classic" });
      } else {
        const fd = new FormData();
        fd.append("file", file as File);
        res = await api.post<PredictResponse>(`/predict/${tab}`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
      setResult(res.data);
    } catch (err) {
      setError(errorMessage(err, "Something went wrong analyzing that input."));
    } finally {
      setBusy(false);
    }
  };

  const canSubmit =
    (tab === "text" && text.trim().length >= 20) ||
    (tab === "url" && url.trim().length >= 8) ||
    ((tab === "image" || tab === "audio") && !!file);

  return (
    <div className="mx-auto max-w-5xl px-6 py-10 md:px-8">
      <PageHeader eyebrow="Case intake" title="Analyze a story">
        Paste text, a link, a screenshot, or an audio clip. Verafide scores the content and hands back a
        verdict with the reasoning and sources behind it.
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <form onSubmit={analyze} className="card p-6">
          <div className="flex flex-wrap items-center gap-2">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => switchTab(id)}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                  tab === id ? "bg-[var(--color-signal)] text-[var(--color-ink)]" : "text-[var(--color-slate)] hover:bg-white/5"
                }`}
              >
                <Icon size={14} /> {label}
              </button>
            ))}
          </div>

          <div className="mt-4">
            {tab === "text" && (
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                required
                minLength={20}
                rows={9}
                placeholder="Paste the headline or article body here…"
                className="w-full resize-none rounded-md border border-[var(--color-line)] bg-[var(--color-ink)] p-3 text-sm leading-relaxed outline-none focus:border-[var(--color-signal)]"
              />
            )}
            {tab === "url" && (
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                placeholder="https://example-news-site.com/article"
                className="w-full rounded-md border border-[var(--color-line)] bg-[var(--color-ink)] p-3 text-sm outline-none focus:border-[var(--color-signal)]"
              />
            )}
            {tab === "image" && (
              <FileDrop
                accept="image/png,image/jpeg,image/webp,image/gif"
                file={file}
                onFile={setFile}
                hint="Drop a screenshot / image, or click to choose (PNG, JPEG, WebP)"
              />
            )}
            {tab === "audio" && (
              <FileDrop
                accept=".mp3,.m4a,.wav,.webm,.ogg,.flac"
                file={file}
                onFile={setFile}
                hint="Drop an audio clip, or click to choose (MP3, M4A, WAV, …)"
              />
            )}
          </div>

          {tab === "text" && (
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button type="button" onClick={() => setText(SAMPLES.fake)} className="font-mono text-[11px] text-[var(--color-slate)] underline decoration-dotted hover:text-[var(--color-paper)]">
                try a flagged sample
              </button>
              <button type="button" onClick={() => setText(SAMPLES.real)} className="font-mono text-[11px] text-[var(--color-slate)] underline decoration-dotted hover:text-[var(--color-paper)]">
                try a verified sample
              </button>
            </div>
          )}

          {error && <p className="mt-3 text-sm text-[var(--color-flagged)]">{error}</p>}

          <button
            type="submit"
            disabled={busy || !canSubmit}
            className="mt-5 flex items-center gap-2 rounded-md bg-[var(--color-signal)] px-5 py-2.5 text-sm font-semibold text-[var(--color-ink)] transition-transform hover:scale-[1.02] disabled:opacity-50"
          >
            <Sparkles size={16} />
            {busy ? "Analyzing…" : "Run analysis"}
          </button>
          {(tab === "image" || tab === "audio") && (
            <p className="mt-2 font-mono text-[11px] text-[var(--color-slate)]">
              {tab === "image"
                ? "Vision model reads the text + manipulation cues; falls back to local OCR if unavailable."
                : "Transcribed with Whisper, then run through the text verdict pipeline."}
            </p>
          )}
        </form>

        <div className="card p-6">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Verdict</p>
          {busy && (
            <div className="mt-10 flex justify-center">
              <Loader label="Reading the story" />
            </div>
          )}
          {!busy && !result && (
            <p className="mt-10 text-center text-sm text-[var(--color-slate)]">Run an analysis to see the stamp land here.</p>
          )}
          {!busy && result && <VerdictPanel result={result} />}
        </div>
      </div>

      {!busy && result && result.analyzed_text && <AssistPanel text={result.analyzed_text} />}
    </div>
  );
}
