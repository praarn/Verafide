import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import api from '../api/client'
import StatCard from '../components/StatCard'
import Loader from '../components/Loader'

export default function Analytics() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get('/analytics/summary')
      .then((res) => setData(res.data))
      .catch(() => setError('Could not load analytics.'))
  }, [])

  if (error) {
    return (
      <div className="mx-auto max-w-5xl px-8 py-10">
        <p className="text-sm text-[var(--color-flagged)]">{error}</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="mx-auto max-w-5xl px-8 py-10">
        <Loader label="Crunching the numbers" />
      </div>
    )
  }

  const pieData = [
    { name: 'Flagged', value: data.fake_count, color: '#B33A3A' },
    { name: 'Verified', value: data.real_count, color: '#1F6F54' },
  ]

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-signal)]">Analytics</p>
      <h1 className="mt-1 font-display text-3xl font-semibold">The desk, at a glance</h1>

      <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Total cases" value={data.total_predictions} accent="signal" />
        <StatCard label="Flagged" value={data.fake_count} accent="flagged" />
        <StatCard label="Verified" value={data.real_count} accent="verified" />
        <StatCard label="Avg. confidence" value={`${Math.round(data.average_confidence * 100)}%`} accent="slate" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-6">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Cases over the last two weeks</p>
          <div className="mt-4 h-64">
            {data.by_day.length === 0 ? (
              <p className="mt-16 text-center text-sm text-[var(--color-slate)]">Not enough recent activity to chart yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.by_day}>
                  <defs>
                    <linearGradient id="fakeGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#B33A3A" stopOpacity={0.5} />
                      <stop offset="95%" stopColor="#B33A3A" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="realGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#1F6F54" stopOpacity={0.5} />
                      <stop offset="95%" stopColor="#1F6F54" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2A2F3A" />
                  <XAxis dataKey="date" stroke="#8891A0" fontSize={11} />
                  <YAxis stroke="#8891A0" fontSize={11} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: '#1A1E28', border: '1px solid #2A2F3A', borderRadius: 8, fontSize: 12 }} />
                  <Area type="monotone" dataKey="fake" stroke="#B33A3A" fill="url(#fakeGrad)" name="Flagged" />
                  <Area type="monotone" dataKey="real" stroke="#1F6F54" fill="url(#realGrad)" name="Verified" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-6">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Verdict split</p>
          <div className="mt-2 h-64">
            {data.total_predictions === 0 ? (
              <p className="mt-16 text-center text-sm text-[var(--color-slate)]">No cases logged yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={80} paddingAngle={3}>
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1A1E28', border: '1px solid #2A2F3A', borderRadius: 8, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-[var(--color-line)] bg-[var(--color-ink-soft)] p-6">
        <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-slate)]">Model performance (held-out test set)</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {['classic', 'advanced'].map((key) => {
            const m = data.model_metrics?.[key]
            if (!m) return null
            return (
              <div key={key} className="rounded-lg border border-[var(--color-line)] p-4">
                <p className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-signal)]">{key}</p>
                <p className="mt-1 text-sm text-[var(--color-slate)]">{m.algorithm}</p>
                <div className="mt-3 grid grid-cols-4 gap-2 text-center">
                  {['accuracy', 'precision', 'recall', 'f1'].map((k) => (
                    <div key={k}>
                      <p className="font-display text-lg font-semibold">{Math.round(m[k] * 100)}%</p>
                      <p className="font-mono text-[10px] uppercase text-[var(--color-slate)]">{k}</p>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
        <p className="mt-4 font-mono text-[11px] text-[var(--color-slate)]">
          Trained on {data.model_metrics?.dataset_size ?? '—'} labeled samples · last trained {data.model_metrics?.trained_at ?? '—'}
        </p>
      </div>
    </div>
  )
}
