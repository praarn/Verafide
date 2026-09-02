"use client";

import { Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import Loader from "@/components/Loader";
import PageHeader from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { HistoryItem } from "@/lib/types";

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<HistoryItem[]>("/history", { params: { limit: 100 } });
      setItems(data);
    } catch {
      setError("Could not load your case history.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const remove = async (id: number) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
    try {
      await api.delete(`/history/${id}`);
    } catch {
      load();
    }
  };

  const clearAll = async () => {
    if (!confirm("Clear your entire case history? This cannot be undone.")) return;
    setItems([]);
    try {
      await api.delete("/history");
    } catch {
      load();
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-6 py-10 md:px-8">
      <div className="mb-8 flex items-start justify-between">
        <PageHeader eyebrow="Case history" title="Every story you've run" />
        {items.length > 0 && (
          <button
            onClick={clearAll}
            className="font-mono text-xs text-[var(--color-slate)] underline decoration-dotted hover:text-[var(--color-flagged)]"
          >
            clear all
          </button>
        )}
      </div>

      {loading && <Loader label="Pulling the case file" />}
      {!loading && error && <p className="text-sm text-[var(--color-flagged)]">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="text-sm text-[var(--color-slate)]">No cases yet — analyses you run will show up here.</p>
      )}

      <div className="space-y-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-start justify-between gap-4 rounded-lg border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-4"
          >
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-[var(--color-slate)]">
                <span>{item.source_type}</span>
                <span>·</span>
                <span>{item.mode}</span>
                <span>·</span>
                <span>{new Date(item.created_at).toLocaleString()}</span>
              </div>
              <p className="mt-1.5 truncate text-sm">{item.input_excerpt}</p>
              {item.source_ref && (
                <p className="mt-0.5 truncate font-mono text-xs text-[var(--color-slate)]">{item.source_ref}</p>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <span
                className="rounded-full px-3 py-1 font-mono text-xs font-semibold"
                style={{
                  backgroundColor: item.label === "real" ? "var(--color-verified-soft)" : "var(--color-flagged-soft)",
                  color: item.label === "real" ? "var(--color-verified)" : "var(--color-flagged)",
                }}
              >
                {item.label === "real" ? "VERIFIED" : "FLAGGED"} · {Math.round(item.confidence * 100)}%
              </span>
              <button
                onClick={() => remove(item.id)}
                aria-label="Delete case"
                className="text-[var(--color-slate)] hover:text-[var(--color-flagged)]"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
