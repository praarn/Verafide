"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api, errorMessage, tokenStore } from "./api";
import type { TokenPair, User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setUser(tokenStore.cachedUser());
    if (!tokenStore.access()) {
      setLoading(false);
      return;
    }
    api
      .get<User>("/auth/me")
      .then(({ data }) => setUser(data))
      .catch(() => {
        tokenStore.clear();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const persist = (data: TokenPair) => {
    tokenStore.save(data);
    setUser(data.user);
  };

  const login = useCallback(async (email: string, password: string) => {
    try {
      const { data } = await api.post<TokenPair>("/auth/login", { email, password });
      persist(data);
    } catch (err) {
      throw new Error(errorMessage(err, "Could not sign in. Check your credentials."));
    }
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    try {
      const { data } = await api.post<TokenPair>("/auth/register", {
        email,
        password,
        full_name: fullName || null,
      });
      persist(data);
    } catch (err) {
      throw new Error(errorMessage(err, "Could not create your account."));
    }
  }, []);

  const logout = useCallback(async () => {
    const refresh = tokenStore.refresh();
    if (refresh) {
      await api.post("/auth/logout", { refresh_token: refresh }).catch(() => {});
    }
    tokenStore.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
