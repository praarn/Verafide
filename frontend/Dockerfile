# Next.js 15 standalone build.

FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# next.config.ts bakes the /api/* rewrite target into the build output, so
# the backend origin must be known here, not just at runtime.
ARG BACKEND_ORIGIN=http://localhost:8000
ARG NEXT_PUBLIC_WS_ORIGIN
ENV BACKEND_ORIGIN=$BACKEND_ORIGIN
ENV NEXT_PUBLIC_WS_ORIGIN=$NEXT_PUBLIC_WS_ORIGIN
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* \
    && addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=build /app/public ./public
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
