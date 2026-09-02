# Frontend (Next.js 15 + TypeScript)

App Router, all pages client components (the app is auth-gated and
dynamic). Tailwind CSS v4 via `@tailwindcss/postcss`; design tokens in
`app/globals.css` `@theme`. Fonts via `next/font/google`.

## Layout

```
src/
  app/
    layout.tsx              <html>, fonts, <AuthProvider>
    globals.css             Tailwind + @theme tokens + keyframes
    page.tsx                landing (server component)
    login/ register/        auth pages
    (dashboard)/
      layout.tsx            protected shell — redirects to /login, sidebar + mobile menu
      analyze/  batch/  history/  analytics/   the four app screens
  components/
    Sidebar, PageHeader, Loader (+Skeleton), StatCard, FileDrop,
    VerdictStamp, VerdictPanel, SourceCredibilityCard, CitationList, AssistPanel
  lib/
    api.ts        axios instance; request interceptor adds the bearer;
                  response interceptor refreshes a 401 once (de-duped) then
                  redirects to /login. tokenStore wraps localStorage. wsOrigin().
    auth.tsx      <AuthProvider> / useAuth — login/register/logout, /auth/me on mount
    types.ts      mirrors backend schemas.py
    verdict.ts    band metadata + verdictWord() + tier colours (shared copy)
    exportCsv.ts  RFC-4180 CSV + BOM, client-side download
    batchJob.ts   runBatchJob(): POST /batch/jobs -> WS stream -> HTTP-poll fallback
```

## Routing / API

`next.config.ts` rewrites `/api/:path*` → `${BACKEND_ORIGIN}/api/:path*`
(default `http://localhost:8000`), so the browser only ever calls
same-origin `/api`. WebSockets can't be rewritten — `wsOrigin()` computes
`ws://<hostname>:8000` (override at build time with
`NEXT_PUBLIC_WS_ORIGIN`).

## Notable screens

- **analyze** — 4 modality tabs (text / URL / image / audio); image & audio
  use `<FileDrop>` (drag-drop). `<VerdictPanel>` renders the stamp,
  confidence-band chip, source-credibility card, RAG `<CitationList>`,
  visual notes / transcript disclosure, and signal words.
- **batch** — `runBatchJob` drives a live progress bar off WS snapshots;
  results table with row expansion + "Export CSV".
- **analytics** — Recharts: 14-day area, verdict pie, input-type bar, plus
  a RAG-index status card and live model metrics.

## Build / checks

`npm run build` (also lints + typechecks), `npm run lint`, `npm run
typecheck`. Docker: multi-stage `output: "standalone"`, non-root.
