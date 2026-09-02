"use client";

import { Loader2, MessageCircle, Send, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { Citation } from "@/lib/types";
import CitationList from "./CitationList";

export default function AssistPanel({ text, label = "this text" }: { text: string; label?: string }) {
  const [tab, setTab] = useState<"summary" | "chat">("summary");

  return (
    <div className="card mt-6 p-6">
      <div className="flex items-center gap-2">
        {(["summary", "chat"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
              tab === t ? "bg-[var(--color-signal)] text-[var(--color-ink)]" : "text-[var(--color-slate)] hover:bg-white/5"
            }`}
          >
            {t === "summary" ? <Sparkles size={14} /> : <MessageCircle size={14} />}
            {t === "summary" ? `Summarize ${label}` : `Ask about ${label}`}
          </button>
        ))}
      </div>
      <div className="mt-4">{tab === "summary" ? <SummaryTab text={text} label={label} /> : <ChatTab text={text} label={label} />}</div>
    </div>
  );
}

function SummaryTab({ text, label }: { text: string; label: string }) {
  const [length, setLength] = useState<"short" | "detailed">("short");
  const [summary, setSummary] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const generate = async () => {
    setBusy(true);
    setError("");
    setSummary("");
    try {
      const { data } = await api.post<{ summary: string }>("/assist/summarize", { text, length });
      setSummary(data.summary);
    } catch (err) {
      setError(errorMessage(err, "Could not generate a summary."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5 rounded-md border border-[var(--color-line)] p-1">
          {(["short", "detailed"] as const).map((l) => (
            <button
              key={l}
              onClick={() => setLength(l)}
              className={`rounded px-2.5 py-1 font-mono text-[11px] uppercase tracking-wide transition-colors ${
                length === l ? "bg-[var(--color-signal)] text-[var(--color-ink)]" : "text-[var(--color-slate)]"
              }`}
            >
              {l}
            </button>
          ))}
        </div>
        <button
          onClick={generate}
          disabled={busy}
          className="flex items-center gap-1.5 rounded-md bg-[var(--color-signal)] px-4 py-1.5 text-xs font-semibold text-[var(--color-ink)] transition-transform hover:scale-[1.02] disabled:opacity-60"
        >
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
          {busy ? "Summarizing…" : summary ? "Regenerate" : "Generate summary"}
        </button>
      </div>
      {error && <p className="mt-3 text-sm text-[var(--color-flagged)]">{error}</p>}
      {summary && <p className="mt-4 whitespace-pre-line text-sm leading-relaxed text-[var(--color-paper)]">{summary}</p>}
      {!summary && !busy && !error && (
        <p className="mt-4 text-sm text-[var(--color-slate)]">Get a quick, neutral summary of {label}.</p>
      )}
    </div>
  );
}

interface Msg {
  role: "user" | "assistant";
  content: string;
}

function ChatTab({ text, label }: { text: string; label: string }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setError("");
    const next = [...messages, { role: "user" as const, content: question }];
    setMessages(next);
    setBusy(true);
    try {
      const { data } = await api.post<{ answer: string; citations: Citation[] }>("/assist/chat", {
        context: text,
        question,
        history: messages,
      });
      setMessages([...next, { role: "assistant", content: data.answer }]);
      setCitations(data.citations || []);
    } catch (err) {
      setError(errorMessage(err, "Could not get a response."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div ref={scrollRef} className="max-h-72 space-y-3 overflow-y-auto scrollbar-thin pr-1">
        {messages.length === 0 && (
          <p className="text-sm text-[var(--color-slate)]">
            Ask anything about {label} — who&rsquo;s quoted, what claims it makes, what&rsquo;s missing.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rounded-lg px-3 py-2 text-sm leading-relaxed ${
              m.role === "user" ? "ml-8 bg-[var(--color-signal)]/15" : "mr-8 bg-black/20"
            } text-[var(--color-paper)]`}
          >
            {m.content}
          </div>
        ))}
        {busy && (
          <div className="mr-8 flex items-center gap-2 rounded-lg bg-black/20 px-3 py-2 text-sm text-[var(--color-slate)]">
            <Loader2 size={13} className="animate-spin" /> thinking…
          </div>
        )}
      </div>
      {error && <p className="mt-2 text-sm text-[var(--color-flagged)]">{error}</p>}
      <form onSubmit={send} className="mt-3 flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Ask a question about ${label}…`}
          className="flex-1 rounded-md border border-[var(--color-line)] bg-[var(--color-ink)] px-3 py-2 text-sm outline-none focus:border-[var(--color-signal)]"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          aria-label="Send question"
          className="flex items-center justify-center rounded-md bg-[var(--color-signal)] p-2.5 text-[var(--color-ink)] transition-transform hover:scale-[1.05] disabled:opacity-60"
        >
          <Send size={15} />
        </button>
      </form>
      {citations.length > 0 && <CitationList citations={citations} title="Answer drew on" />}
    </div>
  );
}
