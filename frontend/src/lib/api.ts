import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import type { TokenPair } from "./types";

const ACCESS_KEY = "verafide_access";
const REFRESH_KEY = "verafide_refresh";
const USER_KEY = "verafide_user";

export const tokenStore = {
  access: () => (typeof window === "undefined" ? null : localStorage.getItem(ACCESS_KEY)),
  refresh: () => (typeof window === "undefined" ? null : localStorage.getItem(REFRESH_KEY)),
  save(pair: TokenPair) {
    localStorage.setItem(ACCESS_KEY, pair.access_token);
    localStorage.setItem(REFRESH_KEY, pair.refresh_token);
    localStorage.setItem(USER_KEY, JSON.stringify(pair.user));
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  },
  cachedUser() {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  },
};

// The Next server proxies /api/* to the FastAPI backend (see next.config.ts).
export const api = axios.create({ baseURL: "/api" });

// WebSockets can't go through the Next rewrite, so the browser hits the
// backend directly. Default assumes the FastAPI dev server on :8000.
export function wsOrigin(): string {
  if (process.env.NEXT_PUBLIC_WS_ORIGIN) return process.env.NEXT_PUBLIC_WS_ORIGIN;
  if (typeof window === "undefined") return "ws://localhost:8000";
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.hostname}:8000`;
}

api.interceptors.request.use((config) => {
  const token = tokenStore.access();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function runRefresh(): Promise<string | null> {
  const refresh = tokenStore.refresh();
  if (!refresh) return null;
  try {
    const { data } = await axios.post<TokenPair>("/api/auth/refresh", { refresh_token: refresh });
    tokenStore.save(data);
    return data.access_token;
  } catch {
    tokenStore.clear();
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const status = error.response?.status;
    const isAuthCall = original?.url?.includes("/auth/");

    if (status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true;
      refreshing = refreshing ?? runRefresh();
      const newToken = await refreshing;
      refreshing = null;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export function errorMessage(err: unknown, fallback = "Something went wrong."): string {
  const ax = err as AxiosError<{ detail?: string }>;
  return ax?.response?.data?.detail || fallback;
}
