import type { NextConfig } from "next";

// REST calls go to /api/* on the same origin and are rewritten to the
// backend in dev. In Docker/prod set BACKEND_ORIGIN (server-side) so the
// Next server proxies to the FastAPI container. WebSocket connections
// cannot be rewritten here — the browser connects straight to
// NEXT_PUBLIC_WS_ORIGIN (see src/lib/api.ts).
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_ORIGIN}/api/:path*` },
    ];
  },
};

export default nextConfig;
