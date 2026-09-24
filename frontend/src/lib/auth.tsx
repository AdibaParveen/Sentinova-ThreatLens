"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, clearTokens, setTokens } from "./api";
import type { NavItem, Preferences, User } from "./types";

type AuthState = {
  user: User | null;
  prefs: Preferences | null;
  navigation: NavItem[];
  loading: boolean;
  login: (
    email: string,
    password: string,
    remember: boolean,
    totp?: string
  ) => Promise<{ mfa?: boolean; preferences?: Preferences | null }>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<{ user: User; preferences: Preferences | null; navigation: NavItem[] } | null>;
};

const Ctx = createContext<AuthState | null>(null);
const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } });

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={qc}>
      <AuthInner>{children}</AuthInner>
    </QueryClientProvider>
  );
}

function AuthInner({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [navigation, setNavigation] = useState<NavItem[]>([]);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    try {
      const data = await api<{ user: User; preferences: Preferences | null; navigation: NavItem[] }>("/api/v1/me");
      setUser(data.user);
      setPrefs(data.preferences);
      setNavigation(data.navigation);
      if (typeof document !== "undefined") {
        document.documentElement.classList.toggle("light", data.preferences?.theme === "light");
      }
      return data;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  const login = useCallback(async (email: string, password: string, remember: boolean, totp?: string) => {
    const data = await api<{
      mfa_required?: boolean;
      access_token?: string;
      refresh_token?: string;
      user?: User;
      navigation?: NavItem[];
    }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, remember_me: remember, totp }),
    });
    if (data.mfa_required) return { mfa: true };
    if (data.access_token) setTokens(data.access_token, data.refresh_token, remember);
    if (data.user) setUser(data.user);
    if (data.navigation) setNavigation(data.navigation);
    const me = await refreshMe();
    return { preferences: me?.preferences };
  }, [refreshMe]);

  const logout = useCallback(async () => {
    try {
      const refresh = typeof window !== "undefined" ? localStorage.getItem("tl_refresh") : null;
      await api("/api/v1/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: refresh || "" }) });
    } catch {
      /* ignore */
    }
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, prefs, navigation, loading, login, logout, refreshMe }),
    [user, prefs, navigation, loading, login, logout, refreshMe]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth");
  return v;
}
