"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import Loader from "@/components/Loader";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";
import type { AnalyticsSummary, RagStatus } from "@/lib/types";

const TOOLTIP_STYLE = { background: "#1A1E28", border: "1px solid #262b36", borderRadius: 8, fontSize: 12 };

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [rag, setRag] = useState<RagStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<AnalyticsSummary>("/analytics/summary").then((r) => setData(r.data)).catch(() => setError("Could not load analytics."));
    api.get<RagStatus>("/rag/status").then((r) => setRag(r.data)).catch(() => {});
  }, []);

  if (error) return <div className="mx-auto max-w-5xl px-8 py-10"><p className="text-sm text-[var(--color-flagged)]">{error}</p></div>;
  if (!data) return <div className="mx-auto max-w-5xl px-8 py-10"><Loader label="Crunching the numbers" /></div>;

  const pieData = [
    { name: "Flagged", value: data.fake_count, color: "#cf5050" },
    { name: "Verified", value: data.real_count, color: "#2f8163" },
  ];
  const modalityData = Object.entries(data.by_modality).map(([name, value]) => ({ name, value }));

  return (
    <div className="mx-auto max-w-5xl px-6 py-10 md:px-8">
      <PageHeader eyebrow="Analytics" title="The desk, at a glance" />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Total cases" value={data.total_predictions} accent="signal" />
        <StatCard label="Flagged" value={data.fake_count} accent="flagged" />
        <StatCard label="Verified" value={data.real_count} accent="verified" />
        <StatCard label="Avg. confidence" value={`${Math.round(data.average_confidence * 100)}%`} accent="slate" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="card p-6">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Cases over the last two weeks</p>
          <div className="mt-4 h-64">
            {data.by_day.length === 0 ? (
              <p className="mt-16 text-center text-sm text-[var(--color-slate)]">Not enough recent activity to chart yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.by_day}>
                  <defs>
                    <linearGradient id="fakeGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#cf5050" stopOpacity={0.5} />
                      <stop offset="95%" stopColor="#cf5050" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="realGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2f8163" stopOpacity={0.5} />
                      <stop offset="95%" stopColor="#2f8163" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#262b36" />
                  <XAxis dataKey="date" stroke="#8891A0" fontSize={11} />
                  <YAxis stroke="#8891A0" fontSize={11} allowDecimals={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Area type="monotone" dataKey="fake" stroke="#cf5050" fill="url(#fakeGrad)" name="Flagged" />
                  <Area type="monotone" dataKey="real" stroke="#2f8163" fill="url(#realGrad)" name="Verified" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="card p-6">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Verdict split</p>
          <div className="mt-2 h-64">
            {data.total_predictions === 0 ? (
              <p className="mt-16 text-center text-sm text-[var(--color-slate)]">No cases logged yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={80} paddingAngle={3}>
                    {pieData.map((e) => (
                      <Cell key={e.name} fill={e.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="card p-6">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Cases by input type</p>
          <div className="mt-4 h-56">
            {modalityData.length === 0 ? (
              <p className="mt-14 text-center text-sm text-[var(--color-slate)]">No cases yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={modalityData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#262b36" />
                  <XAxis dataKey="name" stroke="#8891A0" fontSize={11} />
                  <YAxis stroke="#8891A0" fontSize={11} allowDecimals={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="value" fill="#d3a24a" radius={[4, 4, 0, 0]} name="Cases" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="card p-6">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Retrieval index (RAG)</p>
          {rag ? (
            <div className="mt-4 grid grid-cols-3 gap-3 text-center">
              <IndexStat value={rag.total_chunks} label="chunks" />
              <IndexStat value={rag.media_literacy_docs} label="literacy docs" />
              <IndexStat value={rag.fact_check_entries} label="fact-checks" />
            </div>
          ) : (
            <p className="mt-4 text-sm text-[var(--color-slate)]">Retrieval index status unavailable.</p>
          )}
          {rag?.built_at && (
            <p className="mt-4 font-mono text-[11px] text-[var(--color-slate)]">index built {new Date(rag.built_at).toLocaleString()}</p>
          )}
        </div>
      </div>

      <div className="card mt-6 p-6">
        <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Model performance (held-out test set)</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {(["classic", "advanced"] as const).map((key) => {
            const m = data.model_metrics[key];
            if (!m) return null;
            return (
              <div key={key} className="rounded-lg border border-[var(--color-line)] p-4">
                <p className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-signal)]">{key}</p>
                <p className="mt-1 text-sm text-[var(--color-slate)]">{m.algorithm}</p>
                <div className="mt-3 grid grid-cols-4 gap-2 text-center">
                  {(["accuracy", "precision", "recall", "f1"] as const).map((k) => (
                    <div key={k}>
                      <p className="font-display text-lg font-semibold">{Math.round(m[k] * 100)}%</p>
                      <p className="font-mono text-[10px] uppercase text-[var(--color-slate)]">{k}</p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
        <p className="mt-4 font-mono text-[11px] text-[var(--color-slate)]">
          Trained on {data.model_metrics.dataset_size ?? "—"} labeled samples · last trained {data.model_metrics.trained_at ?? "—"}
        </p>
      </div>
    </div>
  );
}

function IndexStat({ value, label }: { value: number; label: string }) {
  return (
    <div>
      <p className="font-display text-2xl font-semibold text-[var(--color-signal)]">{value}</p>
      <p className="font-mono text-[10px] uppercase text-[var(--color-slate)]">{label}</p>
    </div>
  );
}
